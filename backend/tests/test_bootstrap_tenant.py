"""Tests de `app/bootstrap_tenant.py` -- alta de un gobierno nuevo (tenant + primer
usuario) al adoptar DiagMuni.

Tres niveles:
1. Generador de contraseña (`generar_password_legible`, app/core/security.py): puro,
   sin DB -- estructura del alfabeto, longitud, formato en bloques.
2. Validación de entrada de `crear_gobierno`/`agregar_funcionario`: las validaciones
   corren ANTES de tocar la sesión, así que se ejercitan con un objeto que revienta
   si algo intenta consultarlo -- confirma que el rechazo es real, no que pasó por
   casualidad.
3. Contra Postgres real (`docker compose up db`): creación real, idempotencia,
   `agregar-funcionario` sobre un tenant ya existente (incluida la regresión de que
   el email es único por tenant, no global), `resetear-password`, y que el
   mecanismo de RLS es el real de `app/db/rls.py` (no una copia local) -- se salta
   limpio si no hay Postgres alcanzable, mismo patrón que test_api_seguimiento.py.
"""

import socket
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.bootstrap_tenant import agregar_funcionario, crear_gobierno, resetear_password
from app.core.config import settings
from app.core.security import _ALFABETO_PASSWORD_LEGIBLE, generar_password_legible, verify_password
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant

# --- (1) generador de contraseña -------------------------------------------------


def test_generar_password_legible_longitud_y_formato():
    password = generar_password_legible()
    bloques = password.split("-")
    assert len(bloques) == 4
    assert all(len(bloque) == 4 for bloque in bloques)
    assert len(password) == 19  # 16 caracteres + 3 guiones


def test_generar_password_legible_alfabeto_sin_ambiguedad():
    prohibidos = set("01IOilo")
    # Genera varias para tener una muestra razonable del alfabeto real usado.
    muestra = "".join(generar_password_legible().replace("-", "") for _ in range(30))
    assert not (set(muestra) & prohibidos)
    assert set(muestra) <= set(_ALFABETO_PASSWORD_LEGIBLE)


def test_generar_password_legible_nunca_repite_el_mismo_valor():
    # Con ~92.5 bits de entropía, una colisión en pocas corridas sería indicio de
    # que el generador no es realmente aleatorio.
    generadas = {generar_password_legible() for _ in range(50)}
    assert len(generadas) == 50


# --- (2) validación de entrada, sin tocar la sesión -----------------------------


class _SesionQueRevienta:
    """Cualquier método usado revienta -- confirma que la validación de
    `crear_gobierno` corre antes de cualquier consulta real."""

    def execute(self, *_args, **_kwargs):
        raise AssertionError("crear_gobierno no debía consultar la sesión: la validación debía rechazar antes")


def test_crear_gobierno_rechaza_pais_no_soportado():
    with pytest.raises(ValueError, match="no soportado"):
        crear_gobierno(
            _SesionQueRevienta(),
            nombre="Gobierno de prueba",
            clave="prueba",
            pais="ar",
            email="func@prueba.mx",
            nombre_funcionario="Func",
        )


def test_crear_gobierno_rechaza_email_invalido():
    with pytest.raises(ValueError, match="formato válido"):
        crear_gobierno(
            _SesionQueRevienta(),
            nombre="Gobierno de prueba",
            clave="prueba",
            pais="mx",
            email="no-es-un-email",
            nombre_funcionario="Func",
        )


@pytest.mark.parametrize("clave", ["-prueba", "prueba-", "prue ba", "prueba--dos", "prueba_dos"])
def test_crear_gobierno_rechaza_clave_invalida(clave):
    with pytest.raises(ValueError, match="no es válida"):
        crear_gobierno(
            _SesionQueRevienta(),
            nombre="Gobierno de prueba",
            clave=clave,
            pais="mx",
            email="func@prueba.mx",
            nombre_funcionario="Func",
        )


def test_crear_gobierno_rechaza_nombre_vacio():
    with pytest.raises(ValueError, match="nombre del gobierno"):
        crear_gobierno(
            _SesionQueRevienta(),
            nombre="   ",
            clave="prueba",
            pais="mx",
            email="func@prueba.mx",
            nombre_funcionario="Func",
        )


def test_crear_gobierno_rechaza_nombre_funcionario_vacio():
    with pytest.raises(ValueError, match="nombre del funcionario"):
        crear_gobierno(
            _SesionQueRevienta(),
            nombre="Gobierno de prueba",
            clave="prueba",
            pais="mx",
            email="func@prueba.mx",
            nombre_funcionario="  ",
        )


def test_agregar_funcionario_rechaza_nombre_vacio():
    with pytest.raises(ValueError, match="nombre del funcionario"):
        agregar_funcionario(
            _SesionQueRevienta(), clave="prueba", email="func@prueba.mx", nombre_funcionario="  "
        )


def test_agregar_funcionario_rechaza_email_invalido():
    with pytest.raises(ValueError, match="formato válido"):
        agregar_funcionario(
            _SesionQueRevienta(), clave="prueba", email="no-es-un-email", nombre_funcionario="Func"
        )


# --- (3) contra Postgres real ----------------------------------------------------


def _postgres_real_disponible() -> bool:
    url = urlparse(settings.database_url.replace("postgresql+psycopg", "postgresql", 1))
    try:
        with socket.create_connection((url.hostname or "localhost", url.port or 5432), timeout=2):
            pass
    except OSError:
        return False
    try:
        db = abrir_sesion_tenant(uuid4())
    except Exception:
        return False
    db.close()
    return True


def _limpiar(db, claves: list[str]) -> None:
    """`usuario` tiene RLS forzado -- hay que fijar el contexto al tenant real de
    cada `clave` antes de poder borrar sus filas (una sesión abierta con un
    tenant_id al azar no ve ninguna fila real, así que el DELETE de `usuario` sería
    un no-op silencioso y el DELETE de `tenant` siguiente reventaría por la FK)."""
    try:
        tenants = db.execute(text("SELECT id FROM tenant WHERE clave = ANY(:c)"), {"c": claves}).fetchall()
        for (tenant_id,) in tenants:
            fijar_contexto_tenant(db, tenant_id)
            db.execute(text("DELETE FROM usuario WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tenant WHERE clave = ANY(:c)"), {"c": claves})
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_crear_gobierno_real_luego_idempotente_contra_postgres_real():
    clave = f"prueba-bootstrap-{uuid4().hex[:8]}"
    db = abrir_sesion_tenant(uuid4())
    try:
        resultado = crear_gobierno(
            db,
            nombre="Gobierno de prueba bootstrap",
            clave=clave,
            pais="mx",
            email="func@prueba-bootstrap.mx",
            nombre_funcionario="Func Bootstrap",
        )
        assert resultado is not None
        tenant, usuario, password = resultado
        db.commit()

        assert tenant.clave == clave
        assert usuario.tenant_id == tenant.id
        assert verify_password(password, usuario.password_hash)
        assert len(password.replace("-", "")) == 16

        # Segunda corrida con la misma clave: no-op limpio, sin escribir nada nuevo.
        db2 = abrir_sesion_tenant(uuid4())
        try:
            repetido = crear_gobierno(
                db2,
                nombre="Otro nombre, misma clave",
                clave=clave,
                pais="uy",
                email="otro@correo.mx",
                nombre_funcionario="Otro",
            )
            assert repetido is None
        finally:
            db2.rollback()
            db2.close()
    finally:
        _limpiar(abrir_sesion_tenant(uuid4()), [clave])


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_agregar_funcionario_a_gobierno_existente_contra_postgres_real():
    clave = f"prueba-bootstrap-{uuid4().hex[:8]}"
    db = abrir_sesion_tenant(uuid4())
    try:
        resultado = crear_gobierno(
            db,
            nombre="Gobierno de prueba agregar-funcionario",
            clave=clave,
            pais="mx",
            email="primero@prueba-agregar.mx",
            nombre_funcionario="Primer Funcionario",
        )
        assert resultado is not None
        tenant, primer_usuario, password_primero = resultado
        db.commit()

        db2 = abrir_sesion_tenant(uuid4())
        try:
            resultado_nuevo = agregar_funcionario(
                db2, clave=clave, email="segundo@prueba-agregar.mx", nombre_funcionario="Segundo Funcionario"
            )
            assert resultado_nuevo is not None
            _tenant_devuelto, segundo_usuario, password_segundo = resultado_nuevo
            db2.commit()
        finally:
            db2.close()

        assert password_segundo != password_primero
        assert segundo_usuario.tenant_id == tenant.id

        # Verificación en una tercera sesión: ambos funcionarios son consultables
        # bajo el mismo tenant (usuario tiene RLS forzado).
        db3 = abrir_sesion_tenant(uuid4())
        try:
            fijar_contexto_tenant(db3, tenant.id)
            assert db3.get(type(primer_usuario), primer_usuario.id) is not None
            assert db3.get(type(segundo_usuario), segundo_usuario.id) is not None
        finally:
            db3.close()
    finally:
        _limpiar(abrir_sesion_tenant(uuid4()), [clave])


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_agregar_funcionario_tenant_inexistente_devuelve_none_contra_postgres_real():
    db = abrir_sesion_tenant(uuid4())
    try:
        resultado = agregar_funcionario(
            db, clave="clave-que-no-existe-nunca", email="x@x.mx", nombre_funcionario="X"
        )
        assert resultado is None
    finally:
        db.rollback()
        db.close()


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_agregar_funcionario_email_duplicado_en_mismo_tenant_no_crea_fila_contra_postgres_real():
    clave = f"prueba-bootstrap-{uuid4().hex[:8]}"
    db = abrir_sesion_tenant(uuid4())
    try:
        resultado = crear_gobierno(
            db,
            nombre="Gobierno de prueba email duplicado",
            clave=clave,
            pais="mx",
            email="repetido@prueba-agregar.mx",
            nombre_funcionario="Original",
        )
        assert resultado is not None
        tenant, _usuario, _password = resultado
        db.commit()

        fijar_contexto_tenant(db, tenant.id)
        total_antes = db.execute(
            text("SELECT count(*) FROM usuario WHERE tenant_id = :t"), {"t": str(tenant.id)}
        ).scalar_one()

        db2 = abrir_sesion_tenant(uuid4())
        try:
            repetido = agregar_funcionario(
                db2, clave=clave, email="repetido@prueba-agregar.mx", nombre_funcionario="Intento duplicado"
            )
            assert repetido is None
        finally:
            db2.rollback()
            db2.close()

        fijar_contexto_tenant(db, tenant.id)  # commit()/rollback() de db2 no afecta a db, pero por claridad
        total_despues = db.execute(
            text("SELECT count(*) FROM usuario WHERE tenant_id = :t"), {"t": str(tenant.id)}
        ).scalar_one()
        assert total_despues == total_antes == 1
    finally:
        _limpiar(abrir_sesion_tenant(uuid4()), [clave])


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_agregar_funcionario_mismo_email_en_tenant_distinto_si_funciona_contra_postgres_real():
    """Regresión: el UniqueConstraint de `usuario` es compuesto (tenant_id, email),
    no global -- el mismo email debe poder repetirse en un gobierno distinto."""
    clave_a = f"prueba-bootstrap-a-{uuid4().hex[:8]}"
    clave_b = f"prueba-bootstrap-b-{uuid4().hex[:8]}"
    email_compartido = "compartido@prueba-agregar.mx"
    db = abrir_sesion_tenant(uuid4())
    try:
        resultado_a = crear_gobierno(
            db, nombre="Gobierno A", clave=clave_a, pais="mx", email=email_compartido, nombre_funcionario="Func A"
        )
        assert resultado_a is not None
        db.commit()

        db2 = abrir_sesion_tenant(uuid4())
        try:
            resultado_b = crear_gobierno(
                db2,
                nombre="Gobierno B",
                clave=clave_b,
                pais="uy",
                email="otro@prueba-agregar.mx",
                nombre_funcionario="Func B",
            )
            assert resultado_b is not None
            db2.commit()
        finally:
            db2.close()

        db3 = abrir_sesion_tenant(uuid4())
        try:
            resultado_agregar = agregar_funcionario(
                db3, clave=clave_b, email=email_compartido, nombre_funcionario="Func B repetido"
            )
            assert resultado_agregar is not None
            db3.commit()
        finally:
            db3.close()
    finally:
        _limpiar(abrir_sesion_tenant(uuid4()), [clave_a, clave_b])


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_resetear_password_sobre_usuario_existente_cambia_el_hash_contra_postgres_real():
    clave = f"prueba-bootstrap-{uuid4().hex[:8]}"
    db = abrir_sesion_tenant(uuid4())
    try:
        resultado = crear_gobierno(
            db,
            nombre="Gobierno de prueba reseteo",
            clave=clave,
            pais="mx",
            email="func@prueba-reseteo.mx",
            nombre_funcionario="Func Reseteo",
        )
        assert resultado is not None
        tenant, usuario, password_original = resultado
        db.commit()

        db2 = abrir_sesion_tenant(uuid4())
        try:
            password_nueva = resetear_password(db2, clave=clave, email="func@prueba-reseteo.mx")
            assert password_nueva is not None
            db2.commit()
        finally:
            db2.close()

        assert password_nueva != password_original

        db3 = abrir_sesion_tenant(uuid4())
        try:
            fijar_contexto_tenant(db3, tenant.id)  # usuario tiene RLS forzado
            usuario_actualizado = db3.get(type(usuario), usuario.id)
            assert usuario_actualizado is not None
            assert verify_password(password_nueva, usuario_actualizado.password_hash)
            assert not verify_password(password_original, usuario_actualizado.password_hash)
        finally:
            db3.close()
    finally:
        _limpiar(abrir_sesion_tenant(uuid4()), [clave])


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_resetear_password_usuario_inexistente_devuelve_none_contra_postgres_real():
    clave = f"prueba-bootstrap-{uuid4().hex[:8]}"
    db = abrir_sesion_tenant(uuid4())
    try:
        resultado = crear_gobierno(
            db,
            nombre="Gobierno de prueba sin ese usuario",
            clave=clave,
            pais="mx",
            email="func@prueba-otro.mx",
            nombre_funcionario="Func",
        )
        assert resultado is not None
        db.commit()

        db2 = abrir_sesion_tenant(uuid4())
        try:
            resultado_reseteo = resetear_password(db2, clave=clave, email="no-existe@prueba-otro.mx")
            assert resultado_reseteo is None
        finally:
            db2.rollback()
            db2.close()
    finally:
        _limpiar(abrir_sesion_tenant(uuid4()), [clave])


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_resetear_password_tenant_inexistente_devuelve_none_contra_postgres_real():
    db = abrir_sesion_tenant(uuid4())
    try:
        resultado = resetear_password(db, clave="clave-que-no-existe-nunca", email="x@x.mx")
        assert resultado is None
    finally:
        db.rollback()
        db.close()

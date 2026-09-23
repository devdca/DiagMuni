"""Tests de app/aplicacion/bitacora_correcciones.py. `registrar_correccion` se
prueba con una sesión doble (no hace ninguna consulta, solo `db.add`);
`listar_correcciones` (orden + filtro por `pieza`) necesita Postgres real
porque ejercita un `select`/`where`/`order_by` de verdad -- se salta limpio si
no hay uno alcanzable (mismo criterio que el resto de la suite, ver
test_api_diagnosticos.py)."""

import socket
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.aplicacion.bitacora_correcciones import correcciones_similares, listar_correcciones, registrar_correccion
from app.core.config import settings
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.models import CorreccionIa, Tenant, Usuario


class _SesionFalsa:
    def __init__(self) -> None:
        self.agregados: list[CorreccionIa] = []

    def add(self, obj: CorreccionIa) -> None:
        self.agregados.append(obj)


def test_registrar_correccion_construye_la_fila_y_la_agrega_sin_commitear() -> None:
    db = _SesionFalsa()
    tenant_id, creado_por, tramite_id = uuid4(), uuid4(), uuid4()

    fila = registrar_correccion(
        db,
        tenant_id=tenant_id,
        creado_por=creado_por,
        tramite_id=tramite_id,
        pieza="mecanismo_identidad",
        entrada_llm="muestra su credencial física en ventanilla",
        salida_llm="propio",
        correccion="ninguno",
    )

    assert fila in db.agregados
    assert fila.tenant_id == tenant_id
    assert fila.creado_por == creado_por
    assert fila.tramite_id == tramite_id
    assert fila.pieza == "mecanismo_identidad"
    assert fila.entrada_llm == "muestra su credencial física en ventanilla"
    assert fila.salida_llm == "propio"
    assert fila.correccion == "ninguno"
    assert fila.ruta_llm is None


def test_registrar_correccion_sin_tramite_ni_ruta() -> None:
    db = _SesionFalsa()
    fila = registrar_correccion(
        db,
        tenant_id=uuid4(),
        creado_por=uuid4(),
        pieza="narrativa_plan",
        entrada_llm="prompt resuelto de ejemplo",
        salida_llm="texto generado",
        correccion="texto corregido por el funcionario",
    )
    assert fila.tramite_id is None
    assert fila.ruta_llm is None


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


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_listar_correcciones_filtra_por_pieza_y_ordena_mas_reciente_primero() -> None:
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(
            Tenant(id=tenant_id, nombre="Tenant de prueba bitacora", clave=f"prueba-bitacora-{tenant_id}", pais="mx")
        )
        usuario = Usuario(
            tenant_id=tenant_id,
            email="prueba@bitacora.mx",
            password_hash="x",
            nombre="Usuario de prueba",
            rol="funcionario",
        )
        db.add(usuario)
        db.commit()
        fijar_contexto_tenant(db, tenant_id)
        db.refresh(usuario)

        # Un `db.commit()` por fila (no uno solo al final): `creado_en` usa
        # `func.now()` (hora de INICIO de transacción en Postgres, no del
        # statement) -- 3 inserts en la misma transacción comparten el mismo
        # valor y el orden entre ellos queda indefinido. En producción cada
        # corrección llega en su propio request/transacción, así que esto
        # reproduce ese caso real en vez de uno artificial (verificado en vivo,
        # 2026-09-10: commitear todo junto sí produce el orden equivocado).
        for pieza, entrada, salida, correccion in (
            ("mecanismo_identidad", "e1", "s1", "c1"),
            ("otra_pieza", "e2", "s2", "c2"),
            ("mecanismo_identidad", "e3", "s3", "c3"),
        ):
            registrar_correccion(
                db,
                tenant_id=tenant_id,
                creado_por=usuario.id,
                pieza=pieza,
                entrada_llm=entrada,
                salida_llm=salida,
                correccion=correccion,
            )
            db.commit()
            fijar_contexto_tenant(db, tenant_id)

        todas = listar_correcciones(db)
        assert len(todas) == 3
        assert todas[0].entrada_llm == "e3"  # más reciente primero

        solo_mecanismo = listar_correcciones(db, pieza="mecanismo_identidad")
        assert {f.entrada_llm for f in solo_mecanismo} == {"e1", "e3"}
    finally:
        try:
            db.execute(text("DELETE FROM correccion_ia WHERE tenant_id = :t"), {"t": str(tenant_id)})
            db.execute(text("DELETE FROM usuario WHERE tenant_id = :t"), {"t": str(tenant_id)})
            db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
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
def test_rls_aisla_correcciones_entre_tenants() -> None:
    tenant_a, tenant_b = uuid4(), uuid4()
    db = abrir_sesion_tenant(tenant_a)
    try:
        db.add(Tenant(id=tenant_a, nombre="Tenant A", clave=f"prueba-rls-a-{tenant_a}", pais="mx"))
        db.add(Tenant(id=tenant_b, nombre="Tenant B", clave=f"prueba-rls-b-{tenant_b}", pais="mx"))
        usuario_a = Usuario(tenant_id=tenant_a, email="a@x.mx", password_hash="x", nombre="A", rol="funcionario")
        db.add(usuario_a)
        db.commit()
        fijar_contexto_tenant(db, tenant_a)
        db.refresh(usuario_a)

        registrar_correccion(
            db, tenant_id=tenant_a, creado_por=usuario_a.id, pieza="p", entrada_llm="e", salida_llm="s", correccion="c"
        )
        db.commit()
        fijar_contexto_tenant(db, tenant_a)
        assert len(listar_correcciones(db)) == 1

        db_b = abrir_sesion_tenant(tenant_b)
        try:
            assert listar_correcciones(db_b) == []
        finally:
            db_b.close()
    finally:
        try:
            parametros = {"a": str(tenant_a), "b": str(tenant_b)}
            db.execute(text("DELETE FROM correccion_ia WHERE tenant_id IN (:a, :b)"), parametros)
            db.execute(text("DELETE FROM usuario WHERE tenant_id IN (:a, :b)"), parametros)
            db.execute(text("DELETE FROM tenant WHERE id IN (:a, :b)"), parametros)
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
def test_correcciones_similares_rankea_por_parecido_y_filtra_por_pieza() -> None:
    """Few-shot real (consumidor de la bitácora, ver docstring del módulo) --
    confirma que `correcciones_similares` no es solo "las últimas N": la más
    parecida al texto de consulta debe salir primero aunque no sea la más
    reciente, y una corrección de otra `pieza` nunca debe aparecer."""
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(
            Tenant(id=tenant_id, nombre="Tenant de prueba similitud", clave=f"prueba-similitud-{tenant_id}", pais="mx")
        )
        usuario = Usuario(
            tenant_id=tenant_id,
            email="prueba@similitud.mx",
            password_hash="x",
            nombre="Usuario de prueba",
            rol="funcionario",
        )
        db.add(usuario)
        db.commit()
        fijar_contexto_tenant(db, tenant_id)
        db.refresh(usuario)

        # Mismo motivo que el test de arriba: un commit por fila para que
        # `creado_en` no empate entre ellas.
        for pieza, entrada, correccion in (
            ("mecanismo_identidad", "muestra su credencial física en ventanilla", "propio"),
            ("mecanismo_identidad", "el ciudadano no usa ningún mecanismo de identidad", "ninguno"),
            ("otra_pieza", "muestra su credencial física en ventanilla", "esto no debe salir"),
        ):
            registrar_correccion(
                db,
                tenant_id=tenant_id,
                creado_por=usuario.id,
                pieza=pieza,
                entrada_llm=entrada,
                salida_llm="s",
                correccion=correccion,
            )
            db.commit()
            fijar_contexto_tenant(db, tenant_id)

        similares = correcciones_similares(
            db, pieza="mecanismo_identidad", entrada_llm="enseña su credencial física al llegar a ventanilla"
        )

        assert len(similares) == 2
        # La más parecida textualmente (credencial física en ventanilla) debe
        # quedar primera, aunque se haya insertado antes que la otra.
        assert similares[0].correccion == "propio"
        assert all(c.pieza == "mecanismo_identidad" for c in similares)
    finally:
        try:
            db.execute(text("DELETE FROM correccion_ia WHERE tenant_id = :t"), {"t": str(tenant_id)})
            db.execute(text("DELETE FROM usuario WHERE tenant_id = :t"), {"t": str(tenant_id)})
            db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

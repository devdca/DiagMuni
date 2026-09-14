"""Tests de `app/aplicacion/gestion_usuarios.py` contra Postgres real -- RBAC
(migración 0011): alta, desactivar/reactivar, cambiar rol, el guard de "último
administrador activo", y el autoservicio (cambiar mi contraseña/nombre).

Separado de test_gestion_usuarios.py (validación de entrada, sin Postgres) para
que el `pytestmark` de este archivo no se lleve de encuentro tests que no
necesitan Postgres -- `pytestmark` aplica a TODO el módulo sin importar en qué
línea se declara.
"""

import socket
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.aplicacion import gestion_usuarios
from app.core.config import settings
from app.core.security import verify_password
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.models import Tenant


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


pytestmark = pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)


@pytest.fixture
def tenant_con_admin():
    """Un tenant con un único `admin_gobierno` activo -- el caso donde el guard
    de "último administrador" importa."""
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant de prueba RBAC", clave=f"prueba-rbac-{tenant_id}", pais="mx"))
        db.flush()
        admin, _password = gestion_usuarios._crear_fila_usuario(
            db, tenant_id=tenant_id, email="admin@prueba-rbac.mx", nombre="Admin Original", rol="admin_gobierno"
        )
        db.commit()
        admin_id = admin.id
    finally:
        db.close()

    yield tenant_id, admin_id

    db = abrir_sesion_tenant(tenant_id)
    try:
        db.execute(text("DELETE FROM usuario WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
        db.commit()
    finally:
        db.close()


def test_crear_usuario_admin_gobierno(tenant_con_admin):
    tenant_id, _admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        resultado = gestion_usuarios.crear_usuario(
            db, tenant_id=tenant_id, email="nuevo@prueba-rbac.mx", nombre="Nuevo Funcionario", rol="funcionario"
        )
        assert resultado is not None
        usuario, password = resultado
        db.commit()
        assert usuario.rol == "funcionario"
        assert usuario.activo is True
        assert verify_password(password, usuario.password_hash)
    finally:
        db.close()


def test_crear_usuario_email_duplicado_devuelve_none(tenant_con_admin):
    tenant_id, admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        fijar_contexto_tenant(db, tenant_id)
        repetido = gestion_usuarios.crear_usuario(
            db, tenant_id=tenant_id, email="admin@prueba-rbac.mx", nombre="Otro", rol="funcionario"
        )
        assert repetido is None
    finally:
        db.close()


def test_desactivar_y_reactivar_usuario(tenant_con_admin):
    tenant_id, admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        segundo, _password = gestion_usuarios.crear_usuario(
            db, tenant_id=tenant_id, email="segundo@prueba-rbac.mx", nombre="Segundo", rol="funcionario"
        )
        db.commit()
        fijar_contexto_tenant(db, tenant_id)

        desactivado = gestion_usuarios.desactivar_usuario(db, tenant_id=tenant_id, usuario_id=segundo.id)
        assert desactivado.activo is False
        db.commit()
        fijar_contexto_tenant(db, tenant_id)

        reactivado = gestion_usuarios.reactivar_usuario(db, tenant_id=tenant_id, usuario_id=segundo.id)
        assert reactivado.activo is True
    finally:
        db.close()


def test_desactivar_al_unico_administrador_activo_se_rechaza(tenant_con_admin):
    tenant_id, admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        with pytest.raises(ValueError, match="único administrador"):
            gestion_usuarios.desactivar_usuario(db, tenant_id=tenant_id, usuario_id=admin_id)
    finally:
        db.rollback()
        db.close()


def test_desactivar_admin_permitido_si_hay_otro_admin_activo(tenant_con_admin):
    tenant_id, admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        segundo_admin, _password = gestion_usuarios.crear_usuario(
            db, tenant_id=tenant_id, email="segundo-admin@prueba-rbac.mx", nombre="Segundo Admin", rol="admin_gobierno"
        )
        db.commit()
        fijar_contexto_tenant(db, tenant_id)

        # Con un segundo admin activo, desactivar al primero ya no es el último.
        resultado = gestion_usuarios.desactivar_usuario(db, tenant_id=tenant_id, usuario_id=admin_id)
        assert resultado.activo is False
        assert segundo_admin.rol == "admin_gobierno"
    finally:
        db.close()


def test_cambiar_rol_al_unico_administrador_activo_se_rechaza(tenant_con_admin):
    tenant_id, admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        with pytest.raises(ValueError, match="único administrador"):
            gestion_usuarios.cambiar_rol(db, tenant_id=tenant_id, usuario_id=admin_id, nuevo_rol="funcionario")
    finally:
        db.rollback()
        db.close()


def test_cambiar_rol_de_funcionario_a_admin(tenant_con_admin):
    tenant_id, _admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        funcionario, _password = gestion_usuarios.crear_usuario(
            db, tenant_id=tenant_id, email="asciende@prueba-rbac.mx", nombre="Asciende", rol="funcionario"
        )
        db.commit()
        fijar_contexto_tenant(db, tenant_id)

        actualizado = gestion_usuarios.cambiar_rol(
            db, tenant_id=tenant_id, usuario_id=funcionario.id, nuevo_rol="admin_gobierno"
        )
        assert actualizado.rol == "admin_gobierno"
    finally:
        db.close()


def test_resetear_password_por_id(tenant_con_admin):
    tenant_id, admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        password_nueva = gestion_usuarios.resetear_password_por_id(db, tenant_id=tenant_id, usuario_id=admin_id)
        assert password_nueva is not None
        db.commit()

        fijar_contexto_tenant(db, tenant_id)
        from app.models import Usuario

        usuario = db.get(Usuario, admin_id)
        assert verify_password(password_nueva, usuario.password_hash)
    finally:
        db.close()


def test_cambiar_password_propia_rechaza_password_actual_incorrecta(tenant_con_admin):
    tenant_id, admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        with pytest.raises(ValueError, match="no coincide"):
            gestion_usuarios.cambiar_password_propia(
                db,
                tenant_id=tenant_id,
                usuario_id=admin_id,
                password_actual="esto-no-es-la-actual",
                password_nueva="una-password-nueva-segura",
            )
    finally:
        db.rollback()
        db.close()


def test_actualizar_nombre_propio(tenant_con_admin):
    tenant_id, admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        actualizado = gestion_usuarios.actualizar_nombre_propio(
            db, tenant_id=tenant_id, usuario_id=admin_id, nombre="Admin Renombrado"
        )
        assert actualizado.nombre == "Admin Renombrado"
    finally:
        db.close()


def test_registrar_login_actualiza_ultimo_login_en(tenant_con_admin):
    tenant_id, admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        from app.models import Usuario

        usuario = db.get(Usuario, admin_id)
        assert usuario.ultimo_login_en is None

        gestion_usuarios.registrar_login(db, usuario)
        db.commit()

        fijar_contexto_tenant(db, tenant_id)
        usuario_actualizado = db.get(Usuario, admin_id)
        assert usuario_actualizado.ultimo_login_en is not None
    finally:
        db.close()

"""Tests HTTP de `app/adaptadores/http/admin_usuarios.py` contra Postgres real --
separado de test_api_admin_usuarios.py (que cubre `requerir_admin`, pura, sin DB)
para que el `pytestmark` de este archivo no se lleve de encuentro tests que no
necesitan Postgres -- `pytestmark` aplica a TODO el módulo sin importar en qué
línea se declara. Mismo patrón de llamar a las funciones del router directamente
con un `TokenData` y una sesión real (ver test_api_seguimiento.py)."""

import socket
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.adaptadores.http import admin_usuarios
from app.adaptadores.http.deps import TokenData
from app.core.config import settings
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.models import Tenant
from app.schemas.usuario import CambiarRolRequest, CrearUsuarioRequest


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
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant admin API", clave=f"prueba-admin-api-{tenant_id}", pais="mx"))
        db.flush()
        from app.aplicacion.gestion_usuarios import _crear_fila_usuario

        admin, _password = _crear_fila_usuario(
            db, tenant_id=tenant_id, email="admin@prueba-admin-api.mx", nombre="Admin API", rol="admin_gobierno"
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


def test_listar_devuelve_al_admin_de_la_fixture(tenant_con_admin):
    tenant_id, admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=admin_id, tenant_id=tenant_id, rol="admin_gobierno")
        resultado = admin_usuarios.listar(token, db)
        assert len(resultado) == 1
        assert resultado[0].email == "admin@prueba-admin-api.mx"
    finally:
        db.close()


def test_crear_usuario_via_endpoint(tenant_con_admin):
    tenant_id, admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=admin_id, tenant_id=tenant_id, rol="admin_gobierno")
        payload = CrearUsuarioRequest(nombre="Nuevo Funcionario", email="nuevo@prueba-admin-api.mx", rol="funcionario")
        resultado = admin_usuarios.crear(payload, token, db)
        assert resultado.usuario.rol == "funcionario"
        assert len(resultado.password_temporal.replace("-", "")) == 16
    finally:
        db.close()


def test_crear_usuario_email_duplicado_responde_409(tenant_con_admin):
    tenant_id, admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=admin_id, tenant_id=tenant_id, rol="admin_gobierno")
        payload = CrearUsuarioRequest(nombre="Repetido", email="admin@prueba-admin-api.mx", rol="funcionario")
        with pytest.raises(HTTPException) as exc_info:
            admin_usuarios.crear(payload, token, db)
        assert exc_info.value.status_code == 409
    finally:
        db.rollback()
        db.close()


def test_desactivar_al_unico_admin_responde_400(tenant_con_admin):
    tenant_id, admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=admin_id, tenant_id=tenant_id, rol="admin_gobierno")
        with pytest.raises(HTTPException) as exc_info:
            admin_usuarios.desactivar(admin_id, token, db)
        assert exc_info.value.status_code == 400
    finally:
        db.rollback()
        db.close()


def test_desactivar_usuario_inexistente_responde_404(tenant_con_admin):
    tenant_id, admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=admin_id, tenant_id=tenant_id, rol="admin_gobierno")
        with pytest.raises(HTTPException) as exc_info:
            admin_usuarios.desactivar(uuid4(), token, db)
        assert exc_info.value.status_code == 404
    finally:
        db.rollback()
        db.close()


def test_cambiar_rol_via_endpoint(tenant_con_admin):
    tenant_id, admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=admin_id, tenant_id=tenant_id, rol="admin_gobierno")
        creado = admin_usuarios.crear(
            CrearUsuarioRequest(nombre="Asciende", email="asciende@prueba-admin-api.mx", rol="funcionario"),
            token,
            db,
        )
        fijar_contexto_tenant(db, tenant_id)

        actualizado = admin_usuarios.cambiar_rol(
            creado.usuario.id, CambiarRolRequest(rol="admin_gobierno"), token, db
        )
        assert actualizado.rol == "admin_gobierno"
    finally:
        db.close()


def test_resetear_password_via_endpoint(tenant_con_admin):
    tenant_id, admin_id = tenant_con_admin
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=admin_id, tenant_id=tenant_id, rol="admin_gobierno")
        resultado = admin_usuarios.resetear_password(admin_id, token, db)
        assert len(resultado.password_temporal.replace("-", "")) == 16
    finally:
        db.close()

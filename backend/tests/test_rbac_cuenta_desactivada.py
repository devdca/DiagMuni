"""Regresión de RBAC (migración 0011): una cuenta desactivada no puede iniciar
sesión, y un token ya emitido de una cuenta desactivada a media jornada deja de
servir en la siguiente request -- no hay que esperar a que expire (hasta 8h,
ver settings.jwt_expire_hours). Mismo patrón contra Postgres real que
test_deps_auth.py (el bug vive en la interacción con la fila real de `usuario`,
una sesión espía no lo detectaría)."""

import socket
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.adaptadores.http.deps import get_current_token
from app.aplicacion.gestion_usuarios import _crear_fila_usuario
from app.core.config import settings
from app.core.security import create_access_token
from app.db.rls import abrir_sesion_tenant
from app.models import Tenant, Usuario


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


def _credenciales(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.fixture
def usuario_desactivado():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant desactivado", clave=f"prueba-desact-{tenant_id}", pais="mx"))
        db.flush()
        usuario, _password = _crear_fila_usuario(
            db, tenant_id=tenant_id, email="inactivo@prueba-desact.mx", nombre="Inactivo", rol="funcionario"
        )
        usuario.activo = False
        db.commit()
        usuario_id = usuario.id
    finally:
        db.close()

    yield tenant_id, usuario_id

    from sqlalchemy import text

    db = abrir_sesion_tenant(tenant_id)
    try:
        db.execute(text("DELETE FROM usuario WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
        db.commit()
    finally:
        db.close()


def test_get_current_token_rechaza_usuario_desactivado(usuario_desactivado):
    tenant_id, usuario_id = usuario_desactivado
    token = create_access_token(usuario_id, tenant_id, "funcionario", "Tenant desactivado", "mx", "municipal")

    with pytest.raises(HTTPException) as exc_info:
        get_current_token(_credenciales(token))
    assert exc_info.value.status_code == 401


def test_get_current_token_acepta_usuario_activo(usuario_desactivado):
    """Control: el mismo fixture pero reactivando la cuenta -- confirma que el
    rechazo de arriba es por `activo`, no por algún otro efecto del fixture."""
    tenant_id, usuario_id = usuario_desactivado
    db = abrir_sesion_tenant(tenant_id)
    try:
        from app.db.rls import fijar_contexto_tenant

        fijar_contexto_tenant(db, tenant_id)
        usuario = db.get(Usuario, usuario_id)
        usuario.activo = True
        db.commit()
    finally:
        db.close()

    token = create_access_token(usuario_id, tenant_id, "funcionario", "Tenant desactivado", "mx", "municipal")
    resultado = get_current_token(_credenciales(token))
    assert resultado.usuario_id == usuario_id

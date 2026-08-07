"""Regresión directa del hallazgo crítico de Strix (JWT forjable -> bypass de
autenticación y de aislamiento multi-tenant): antes de este fix, `get_current_token`
(app/api/deps.py) confiaba en `sub`/`tenant_id`/`rol` del JWT sin verificar nada
contra la base de datos -- un token con firma válida pero datos inventados pasaba
igual. Contra Postgres real (RLS incluido) porque el bug vive exactamente en la
interacción entre el claim confiado y la policy RLS -- una sesión espía no lo
detectaría (mismo criterio que test_api_seguimiento.py)."""

import socket
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import text

from app.api.deps import get_current_token
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


def _credenciales(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


pytestmark = pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)


@pytest.fixture
def gobierno_y_funcionario():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant de prueba auth", clave=f"prueba-auth-{tenant_id}", pais="uy"))
        db.flush()
        usuario = Usuario(
            tenant_id=tenant_id, email="funcionario@prueba.gub.uy", password_hash="x", nombre="Funcionario de prueba"
        )
        db.add(usuario)
        db.flush()
        db.commit()
        usuario_id = usuario.id
    finally:
        db.close()

    yield tenant_id, usuario_id

    db = abrir_sesion_tenant(tenant_id)
    try:
        db.execute(text("DELETE FROM usuario WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
        db.commit()
    finally:
        db.close()


def test_token_valido_de_usuario_real_resuelve_desde_la_base_de_datos(gobierno_y_funcionario):
    tenant_id, usuario_id = gobierno_y_funcionario
    token = create_access_token(usuario_id, tenant_id, "funcionario", "Tenant de prueba auth", "uy")

    resultado = get_current_token(_credenciales(token))

    assert resultado.usuario_id == usuario_id
    assert resultado.tenant_id == tenant_id
    assert resultado.rol == "funcionario"


def test_regresion_token_con_usuario_inventado_se_rechaza(gobierno_y_funcionario):
    """El caso exacto del hallazgo crítico: firma válida (mismo JWT_SECRET real),
    pero `sub` no corresponde a ningún usuario existente. Antes del fix esto
    generaba un TokenData igual de válido a ojos del resto de la aplicación."""
    tenant_id, _usuario_real = gobierno_y_funcionario
    usuario_inventado = uuid4()
    token_forjado = create_access_token(usuario_inventado, tenant_id, "funcionario", "Tenant de prueba auth", "uy")

    with pytest.raises(HTTPException) as exc_info:
        get_current_token(_credenciales(token_forjado))
    assert exc_info.value.status_code == 401


def test_regresion_token_con_tenant_id_de_otro_gobierno_se_rechaza(gobierno_y_funcionario):
    """Un usuario real, pero el token reclama pertenencia a un tenant distinto del
    suyo -- ej. un token viejo tras mover al usuario de gobierno, o un intento de
    escalar el tenant_id manteniendo un `sub` real. `usuario.tenant_id` (columna
    real) debe ganarle siempre al claim."""
    tenant_id_real, usuario_id = gobierno_y_funcionario
    tenant_id_ajeno = uuid4()
    token_con_tenant_equivocado = create_access_token(
        usuario_id, tenant_id_ajeno, "funcionario", "Otro gobierno", "mx"
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_token(_credenciales(token_con_tenant_equivocado))
    assert exc_info.value.status_code == 401

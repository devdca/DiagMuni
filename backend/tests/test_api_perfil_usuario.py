"""Tests HTTP de `app/adaptadores/http/perfil_usuario.py` -- autoservicio del
propio usuario autenticado (cualquier rol), mismo patrón de test_api_seguimiento.py."""

import socket
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.adaptadores.http import perfil_usuario
from app.adaptadores.http.deps import TokenData
from app.core.config import settings
from app.core.security import verify_password
from app.db.rls import abrir_sesion_tenant
from app.models import Tenant, Usuario
from app.schemas.usuario import ActualizarPerfilRequest, CambiarPasswordPropiaRequest


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
def tenant_con_funcionario():
    from app.aplicacion.gestion_usuarios import _crear_fila_usuario

    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant perfil", clave=f"prueba-perfil-{tenant_id}", pais="mx"))
        db.flush()
        usuario, password = _crear_fila_usuario(
            db, tenant_id=tenant_id, email="func@prueba-perfil.mx", nombre="Func Perfil", rol="funcionario"
        )
        db.commit()
        usuario_id = usuario.id
    finally:
        db.close()

    yield tenant_id, usuario_id, password

    db = abrir_sesion_tenant(tenant_id)
    try:
        db.execute(text("DELETE FROM usuario WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
        db.commit()
    finally:
        db.close()


def test_obtener_mi_perfil(tenant_con_funcionario):
    tenant_id, usuario_id, _password = tenant_con_funcionario
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=usuario_id, tenant_id=tenant_id, rol="funcionario")
        resultado = perfil_usuario.obtener_mi_perfil(token, db)
        assert resultado.email == "func@prueba-perfil.mx"
    finally:
        db.close()


def test_actualizar_mi_perfil_cambia_el_nombre(tenant_con_funcionario):
    tenant_id, usuario_id, _password = tenant_con_funcionario
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=usuario_id, tenant_id=tenant_id, rol="funcionario")
        resultado = perfil_usuario.actualizar_mi_perfil(ActualizarPerfilRequest(nombre="Nombre Nuevo"), token, db)
        assert resultado.nombre == "Nombre Nuevo"
    finally:
        db.close()


def test_cambiar_mi_password(tenant_con_funcionario):
    tenant_id, usuario_id, password_original = tenant_con_funcionario
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=usuario_id, tenant_id=tenant_id, rol="funcionario")
        perfil_usuario.cambiar_mi_password(
            CambiarPasswordPropiaRequest(password_actual=password_original, password_nueva="una-password-bien-larga"),
            token,
            db,
        )
        db.commit()

        from app.db.rls import fijar_contexto_tenant

        fijar_contexto_tenant(db, tenant_id)
        usuario = db.get(Usuario, usuario_id)
        assert verify_password("una-password-bien-larga", usuario.password_hash)
    finally:
        db.close()


def test_cambiar_mi_password_rechaza_password_actual_incorrecta(tenant_con_funcionario):
    tenant_id, usuario_id, _password_original = tenant_con_funcionario
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=usuario_id, tenant_id=tenant_id, rol="funcionario")
        with pytest.raises(HTTPException) as exc_info:
            perfil_usuario.cambiar_mi_password(
                CambiarPasswordPropiaRequest(password_actual="incorrecta", password_nueva="una-password-bien-larga"),
                token,
                db,
            )
        assert exc_info.value.status_code == 400
    finally:
        db.rollback()
        db.close()

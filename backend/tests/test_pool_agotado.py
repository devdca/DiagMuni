"""Auditoría de seguridad H-12: el pool de conexiones a Postgres se agotaba bajo
carga concurrente y el timeout de checkout se propagaba como un 500 genérico.
Cubre el exception handler de app/main.py que lo convierte en 503 + Retry-After."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

from app.api import deps
from app.core.security import create_access_token
from app.main import app, pool_agotado

client = TestClient(app)


def test_pool_agotado_responde_503_con_retry_after():
    response = pool_agotado(None, SQLAlchemyTimeoutError())
    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"


def test_timeout_de_pool_durante_una_peticion_real_responde_503(monkeypatch):
    def _pool_agotado(_tenant_id):
        raise SQLAlchemyTimeoutError("QueuePool limit of size 5 overflow 10 reached")

    monkeypatch.setattr(deps, "abrir_sesion_tenant", _pool_agotado)

    token = create_access_token(
        usuario_id=uuid4(), tenant_id=uuid4(), rol="funcionario", nombre_gobierno="Prueba", pais="mx"
    )
    response = client.get(
        f"/api/tramites/{uuid4()}/diagnostico", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"

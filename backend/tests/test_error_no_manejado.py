"""Handler catch-all de app/main.py: cualquier excepción sin handler propio debe
devolver JSON consistente con el resto de la API (nunca el texto plano "Internal
Server Error" de Starlette) y sin fugar el detalle interno de la excepción al
cliente -- ese detalle solo va al log de stdout, para diagnóstico vía
`docker compose logs backend`."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app import main
from app.adaptadores.http import deps
from app.core.security import create_access_token
from app.main import app

# raise_server_exceptions=False: el handler de Exception (a diferencia de los
# handlers "normales" de app/main.py) queda registrado en ServerErrorMiddleware,
# no en ExceptionMiddleware -- Starlette re-lanza la excepción original ahí
# después de enviar la respuesta (para que Uvicorn la loguee en un despliegue
# real). Sin esta bandera, TestClient reproduce ese re-lanzamiento como si la
# excepción se hubiera escapado del todo, en vez de dejarnos ver la respuesta
# que sí llegó al cliente real.
client = TestClient(app, raise_server_exceptions=False)


def test_error_no_manejado_no_fuga_el_detalle_de_la_excepcion(monkeypatch):
    def _falla(_tenant_id):
        raise ValueError("DATABASE_URL=postgresql://user:supersecret@host/db")

    monkeypatch.setattr(deps, "abrir_sesion_tenant", _falla)

    token = create_access_token(
        usuario_id=uuid4(),
        tenant_id=uuid4(),
        rol="funcionario",
        nombre_gobierno="Prueba",
        pais="mx",
        nivel_gobierno="municipal",
    )
    response = client.get(
        f"/api/tramites/{uuid4()}/diagnostico", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body == {"detail": "Ocurrió un error interno. Intenta de nuevo más tarde."}
    assert "supersecret" not in response.text
    assert "ValueError" not in response.text


def test_error_no_manejado_reporta_a_sentry_explicitamente(monkeypatch):
    """El handler está registrado para `Exception` -- Starlette lo enruta a
    `ServerErrorMiddleware`, que la integración de Sentry no parchea (a
    diferencia de `ExceptionMiddleware`) -- ver app/core/observabilidad.py. Sin
    un `capture_exception` explícito acá, esto nunca llegaría a Sentry."""
    llamadas = []
    monkeypatch.setattr(main.sentry_sdk, "capture_exception", llamadas.append)

    def _falla(_tenant_id):
        raise ValueError("boom")

    monkeypatch.setattr(deps, "abrir_sesion_tenant", _falla)

    token = create_access_token(
        usuario_id=uuid4(),
        tenant_id=uuid4(),
        rol="funcionario",
        nombre_gobierno="Prueba",
        pais="mx",
        nivel_gobierno="municipal",
    )
    client.get(f"/api/tramites/{uuid4()}/diagnostico", headers={"Authorization": f"Bearer {token}"})

    assert len(llamadas) == 1
    assert isinstance(llamadas[0], ValueError)


def test_pool_agotado_sigue_teniendo_prioridad_sobre_el_catch_all(monkeypatch):
    """El handler específico de SQLAlchemyTimeoutError (H-12) no debe quedar
    tapado por el catch-all nuevo -- Starlette resuelve por MRO, pero se deja
    un test explícito para no depender de ese detalle de implementación."""
    from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

    def _pool_agotado(_tenant_id):
        raise SQLAlchemyTimeoutError("QueuePool limit of size 5 overflow 10 reached")

    monkeypatch.setattr(deps, "abrir_sesion_tenant", _pool_agotado)

    token = create_access_token(
        usuario_id=uuid4(),
        tenant_id=uuid4(),
        rol="funcionario",
        nombre_gobierno="Prueba",
        pais="mx",
        nivel_gobierno="municipal",
    )
    response = client.get(
        f"/api/tramites/{uuid4()}/diagnostico", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"

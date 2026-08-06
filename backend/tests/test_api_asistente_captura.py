"""Tests HTTP (TestClient) de los endpoints nuevos de asistencia de captura F1.

Enfoque elegido para esta tarea: `TestClient` real sobre `app.main.app`, con
`dependency_overrides` de `get_current_token`/`get_db` (evita depender de Postgres
real -- estos endpoints solo necesitan resolver `Tenant.pais`, no todo el resto del
esquema) y monkeypatch de las dos funciones de `app.ia.asistente_captura` para no
llamar nunca a un LLM real, mismo principio que
`backend/tests/test_asistente_captura.py` pero a nivel HTTP en vez de función pura
-- este módulo sí depende del grafo de dependencias de FastAPI (auth + Tenant), a
diferencia de aquel. No se expande esta infraestructura a ningún otro router ya
existente (alcance de esta tarea, no scope creep)."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import asistente_captura as asistente_captura_api
from app.api.deps import TokenData, get_current_token, get_db
from app.main import app

client = TestClient(app)


class _TenantFalso:
    def __init__(self, pais: str) -> None:
        self.pais = pais


class _SesionFalsa:
    """Doble de `Session` -- solo implementa `.get(modelo, id)`, lo único que usa
    el endpoint de mecanismo_identidad para resolver `Tenant`."""

    def __init__(self, tenant: _TenantFalso | None) -> None:
        self._tenant = tenant

    def get(self, _modelo: object, _id: object) -> _TenantFalso | None:
        return self._tenant


@pytest.fixture(autouse=True)
def _limpiar_overrides():
    yield
    app.dependency_overrides.clear()


def _autenticar() -> None:
    app.dependency_overrides[get_current_token] = lambda: TokenData(
        usuario_id=uuid4(), tenant_id=uuid4(), rol="funcionario"
    )


def _sesion_con_tenant(pais: str | None) -> None:
    tenant = _TenantFalso(pais) if pais is not None else None
    app.dependency_overrides[get_db] = lambda: _SesionFalsa(tenant)


# === /consistencia-booleana =======================================================


def test_consistencia_booleana_requiere_sesion() -> None:
    respuesta = client.post(
        "/api/asistente-captura/consistencia-booleana",
        json={"texto_aclaracion": "texto", "valor_marcado": True},
    )
    assert respuesta.status_code in (401, 403)


def test_consistencia_booleana_devuelve_categoria(monkeypatch: pytest.MonkeyPatch) -> None:
    _autenticar()
    _sesion_con_tenant("mx")
    monkeypatch.setattr(
        asistente_captura_api, "clasificar_consistencia_booleana", lambda texto, valor: "consistente"
    )

    respuesta = client.post(
        "/api/asistente-captura/consistencia-booleana",
        json={"texto_aclaracion": "todo en orden", "valor_marcado": True},
        headers={"Authorization": "Bearer x"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"categoria": "consistente"}


def test_consistencia_booleana_nunca_persiste_nada_no_toca_la_sesion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Este endpoint nunca debe llamar db.get/add/commit -- solo clasifica."""
    _autenticar()

    class _SesionQueFallaSiSeUsa:
        def get(self, *args, **kwargs):
            raise AssertionError("consistencia-booleana no debería tocar la sesión")

    app.dependency_overrides[get_db] = lambda: _SesionQueFallaSiSeUsa()
    monkeypatch.setattr(
        asistente_captura_api, "clasificar_consistencia_booleana", lambda texto, valor: "no_concluyente"
    )

    respuesta = client.post(
        "/api/asistente-captura/consistencia-booleana",
        json={"texto_aclaracion": "texto ambiguo", "valor_marcado": False},
        headers={"Authorization": "Bearer x"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"categoria": "no_concluyente"}


# === /mecanismo-identidad ==========================================================


def test_mecanismo_identidad_requiere_sesion() -> None:
    respuesta = client.post(
        "/api/asistente-captura/mecanismo-identidad",
        json={"texto_aclaracion": "texto"},
    )
    assert respuesta.status_code in (401, 403)


def test_mecanismo_identidad_resuelve_pais_desde_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    _autenticar()
    _sesion_con_tenant("uy")

    paises_recibidos = []

    def _espia(texto: str, pais: str) -> str:
        paises_recibidos.append(pais)
        return "id_uruguay"

    monkeypatch.setattr(asistente_captura_api, "clasificar_mecanismo_identidad", _espia)

    respuesta = client.post(
        "/api/asistente-captura/mecanismo-identidad",
        json={"texto_aclaracion": "usamos la cédula nacional"},
        headers={"Authorization": "Bearer x"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"categoria": "id_uruguay"}
    assert paises_recibidos == ["uy"]


def test_mecanismo_identidad_ignora_cualquier_pais_que_mande_el_cliente(monkeypatch: pytest.MonkeyPatch) -> None:
    """El schema de request ni siquiera declara un campo `pais` -- si el cliente lo
    manda de todos modos, Pydantic lo ignora (extra no declarado por default) y el
    servidor sigue resolviendo el país real desde `Tenant`, nunca del body."""
    _autenticar()
    _sesion_con_tenant("mx")

    paises_recibidos = []

    def _espia(texto: str, pais: str) -> str:
        paises_recibidos.append(pais)
        return "propio"

    monkeypatch.setattr(asistente_captura_api, "clasificar_mecanismo_identidad", _espia)

    respuesta = client.post(
        "/api/asistente-captura/mecanismo-identidad",
        json={"texto_aclaracion": "texto", "pais": "uy"},
        headers={"Authorization": "Bearer x"},
    )

    assert respuesta.status_code == 200
    assert paises_recibidos == ["mx"]


def test_mecanismo_identidad_404_si_tenant_no_existe(monkeypatch: pytest.MonkeyPatch) -> None:
    _autenticar()
    _sesion_con_tenant(None)

    def _no_debe_llamarse(*args: object, **kwargs: object) -> str:
        raise AssertionError("no debía clasificar sin poder resolver el tenant")

    monkeypatch.setattr(asistente_captura_api, "clasificar_mecanismo_identidad", _no_debe_llamarse)

    respuesta = client.post(
        "/api/asistente-captura/mecanismo-identidad",
        json={"texto_aclaracion": "texto"},
        headers={"Authorization": "Bearer x"},
    )
    assert respuesta.status_code == 404

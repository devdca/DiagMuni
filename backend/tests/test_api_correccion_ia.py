"""Tests HTTP (TestClient) de POST/GET /api/correcciones-ia (backend/app/
adaptadores/http/correccion_ia.py). POST usa una sesión doble (solo ejercita
`db.add`/`db.commit`/`db.refresh`); GET se prueba parcheando `listar_correcciones`
en el módulo del router -- el filtrado/orden real ya se cubre contra Postgres
real en test_bitacora_correcciones.py."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.adaptadores.http import correccion_ia as correccion_ia_router
from app.adaptadores.http.deps import TokenData, get_current_token, get_db
from app.main import app
from app.models import CorreccionIa

client = TestClient(app)


class _SesionFalsa:
    def __init__(self) -> None:
        self.agregados: list[CorreccionIa] = []

    def add(self, obj: CorreccionIa) -> None:
        obj.id = uuid4()
        obj.creado_en = datetime.now(UTC)
        self.agregados.append(obj)

    def commit(self) -> None:
        pass

    def refresh(self, _obj: object) -> None:
        pass


@pytest.fixture(autouse=True)
def _limpiar_overrides():
    yield
    app.dependency_overrides.clear()


def _autenticar(tenant_id, rol: str = "funcionario") -> None:
    app.dependency_overrides[get_current_token] = lambda: TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol=rol)


def test_post_requiere_sesion() -> None:
    respuesta = client.post("/api/correcciones-ia", json={})
    assert respuesta.status_code in (401, 403)


def test_post_cualquier_rol_autenticado_puede_registrar() -> None:
    tenant_id = uuid4()
    _autenticar(tenant_id, rol="funcionario")
    app.dependency_overrides[get_db] = lambda: _SesionFalsa()

    payload = {
        "pieza": "mecanismo_identidad",
        "entrada_llm": "muestra su credencial física en ventanilla",
        "salida_llm": "propio",
        "correccion": "ninguno",
    }
    respuesta = client.post(
        "/api/correcciones-ia", json=payload, headers={"Authorization": "Bearer x"}
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["pieza"] == "mecanismo_identidad"
    assert cuerpo["correccion"] == "ninguno"
    assert cuerpo["tramite_id"] is None
    assert cuerpo["ruta_llm"] is None


def test_post_campo_vacio_responde_422() -> None:
    tenant_id = uuid4()
    _autenticar(tenant_id)
    app.dependency_overrides[get_db] = lambda: _SesionFalsa()

    respuesta = client.post(
        "/api/correcciones-ia",
        json={"pieza": "", "entrada_llm": "e", "salida_llm": "s", "correccion": "c"},
        headers={"Authorization": "Bearer x"},
    )
    assert respuesta.status_code == 422


def test_get_requiere_sesion() -> None:
    respuesta = client.get("/api/correcciones-ia")
    assert respuesta.status_code in (401, 403)


def test_get_requiere_rol_admin() -> None:
    tenant_id = uuid4()
    _autenticar(tenant_id, rol="funcionario")
    app.dependency_overrides[get_db] = lambda: _SesionFalsa()

    respuesta = client.get("/api/correcciones-ia", headers={"Authorization": "Bearer x"})
    assert respuesta.status_code == 403


def test_get_admin_devuelve_lo_que_lista_la_capa_de_aplicacion(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid4()
    _autenticar(tenant_id, rol="admin_gobierno")
    app.dependency_overrides[get_db] = lambda: _SesionFalsa()

    fila = CorreccionIa(
        id=uuid4(),
        tenant_id=tenant_id,
        tramite_id=None,
        pieza="mecanismo_identidad",
        entrada_llm="e",
        salida_llm="s",
        correccion="c",
        ruta_llm=None,
        creado_por=uuid4(),
        creado_en=datetime.now(UTC),
    )
    llamadas: list[str | None] = []

    def _listar_falso(_db: object, *, pieza: str | None = None, limite: int = 200) -> list[CorreccionIa]:
        llamadas.append(pieza)
        return [fila]

    monkeypatch.setattr(correccion_ia_router, "listar_correcciones", _listar_falso)

    respuesta = client.get(
        "/api/correcciones-ia", params={"pieza": "mecanismo_identidad"}, headers={"Authorization": "Bearer x"}
    )
    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]["pieza"] == "mecanismo_identidad"
    assert llamadas == ["mecanismo_identidad"]

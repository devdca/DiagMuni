"""Tests HTTP (TestClient) de GET/PUT /api/gobierno/contexto (backend/app/api/
gobierno_contexto.py). Mismo enfoque que test_api_asistente_captura.py:
`TestClient` real sobre `app.main.app` con `dependency_overrides` de
`get_current_token`/`get_db`, sin Postgres real -- el router solo hace
`db.execute(select(...))`, `db.add`, `db.commit`, `db.refresh`, todo reproducible
con una sesión doble en memoria."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import TokenData, get_current_token, get_db
from app.main import app
from app.models import ContextoInstitucional

client = TestClient(app)


class _ResultadoFalso:
    def __init__(self, valor: object) -> None:
        self._valor = valor

    def scalar_one_or_none(self) -> object:
        return self._valor


class _SesionFalsaContexto:
    """Doble de `Session` -- una sola fila en memoria por tenant (o ninguna),
    suficiente para ejercitar `_obtener_fila`/`guardar_contexto` sin Postgres."""

    def __init__(self, fila: ContextoInstitucional | None = None) -> None:
        self.fila = fila
        self.agregados: list[object] = []
        self.commits = 0

    def execute(self, _stmt: object) -> _ResultadoFalso:
        return _ResultadoFalso(self.fila)

    def add(self, obj: object) -> None:
        self.agregados.append(obj)
        self.fila = obj  # la siguiente lectura dentro del mismo request ya lo ve

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, _obj: object) -> None:
        pass


@pytest.fixture(autouse=True)
def _limpiar_overrides():
    yield
    app.dependency_overrides.clear()


def _autenticar(tenant_id) -> None:
    app.dependency_overrides[get_current_token] = lambda: TokenData(
        usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario"
    )


def _con_sesion(fila: ContextoInstitucional | None = None) -> _SesionFalsaContexto:
    sesion = _SesionFalsaContexto(fila)
    app.dependency_overrides[get_db] = lambda: sesion
    return sesion


# === GET ============================================================================


def test_get_requiere_sesion() -> None:
    respuesta = client.get("/api/gobierno/contexto")
    assert respuesta.status_code in (401, 403)


def test_get_sin_fila_previa_nunca_404_sintetiza_shape_con_8_campos_en_null() -> None:
    tenant_id = uuid4()
    _autenticar(tenant_id)
    _con_sesion(None)

    respuesta = client.get("/api/gobierno/contexto", headers={"Authorization": "Bearer x"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["tenant_id"] == str(tenant_id)
    campos_de_negocio = [
        "poblacion_total",
        "personal_total_gobierno",
        "presupuesto_tic_anual",
        "area_tic_existe",
        "conectividad",
        "normativa_local_emitida",
        "autoridad_gobernanza_digital",
        "actualizado_en",
    ]
    assert len(campos_de_negocio) == 8
    for campo in campos_de_negocio:
        assert cuerpo[campo] is None


def test_get_con_fila_existente_devuelve_sus_valores() -> None:
    tenant_id = uuid4()
    _autenticar(tenant_id)
    fila = ContextoInstitucional(
        tenant_id=tenant_id,
        poblacion_total=5000,
        personal_total_gobierno=30,
        presupuesto_tic_anual=None,
        area_tic_existe=True,
        conectividad="estable",
        normativa_local_emitida=False,
        autoridad_gobernanza_digital=False,
        actualizado_en=datetime(2026, 8, 1, tzinfo=UTC),
    )
    _con_sesion(fila)

    respuesta = client.get("/api/gobierno/contexto", headers={"Authorization": "Bearer x"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["poblacion_total"] == 5000
    assert cuerpo["area_tic_existe"] is True
    assert cuerpo["conectividad"] == "estable"
    assert cuerpo["autoridad_gobernanza_digital"] is False


# === PUT -- upsert parcial ===========================================================


def test_put_requiere_sesion() -> None:
    respuesta = client.put("/api/gobierno/contexto", json={"poblacion_total": 100})
    assert respuesta.status_code in (401, 403)


def test_put_sin_fila_previa_crea_una_nueva_con_solo_los_campos_enviados() -> None:
    tenant_id = uuid4()
    _autenticar(tenant_id)
    sesion = _con_sesion(None)

    respuesta = client.put(
        "/api/gobierno/contexto",
        json={"poblacion_total": 12000},
        headers={"Authorization": "Bearer x"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["poblacion_total"] == 12000
    assert cuerpo["area_tic_existe"] is None
    assert cuerpo["actualizado_en"] is not None
    assert sesion.commits == 1
    assert len(sesion.agregados) == 1


def test_put_con_fila_existente_actualiza_solo_el_campo_enviado_preserva_el_resto() -> None:
    tenant_id = uuid4()
    _autenticar(tenant_id)
    fila = ContextoInstitucional(
        tenant_id=tenant_id,
        poblacion_total=5000,
        area_tic_existe=True,
        conectividad="estable",
        autoridad_gobernanza_digital=True,
    )
    sesion = _con_sesion(fila)

    respuesta = client.put(
        "/api/gobierno/contexto",
        json={"autoridad_gobernanza_digital": False},
        headers={"Authorization": "Bearer x"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["autoridad_gobernanza_digital"] is False
    # el resto de los campos no enviados en este PUT no se pisan (upsert parcial)
    assert cuerpo["poblacion_total"] == 5000
    assert cuerpo["area_tic_existe"] is True
    assert cuerpo["conectividad"] == "estable"
    assert sesion.commits == 1
    assert len(sesion.agregados) == 0  # no crea una fila nueva, actualiza la existente


def test_put_reescribe_actualizado_en_en_cada_llamada_exitosa() -> None:
    tenant_id = uuid4()
    _autenticar(tenant_id)
    fila = ContextoInstitucional(
        tenant_id=tenant_id, actualizado_en=datetime(2020, 1, 1, tzinfo=UTC)
    )
    _con_sesion(fila)

    respuesta = client.put(
        "/api/gobierno/contexto",
        json={"poblacion_total": 1},
        headers={"Authorization": "Bearer x"},
    )

    assert respuesta.status_code == 200
    actualizado_en = datetime.fromisoformat(respuesta.json()["actualizado_en"])
    assert actualizado_en.year >= 2026


# === PUT -- validación 422 en español llano =========================================


def test_put_poblacion_negativa_devuelve_422() -> None:
    _autenticar(uuid4())
    _con_sesion(None)

    respuesta = client.put(
        "/api/gobierno/contexto",
        json={"poblacion_total": -1},
        headers={"Authorization": "Bearer x"},
    )

    assert respuesta.status_code == 422
    assert "negativo" in str(respuesta.json()["detail"]).lower()


def test_put_presupuesto_negativo_devuelve_422() -> None:
    _autenticar(uuid4())
    _con_sesion(None)

    respuesta = client.put(
        "/api/gobierno/contexto",
        json={"presupuesto_tic_anual": -500},
        headers={"Authorization": "Bearer x"},
    )

    assert respuesta.status_code == 422
    assert "negativo" in str(respuesta.json()["detail"]).lower()


def test_put_conectividad_invalida_devuelve_422_con_opciones_validas() -> None:
    _autenticar(uuid4())
    _con_sesion(None)

    respuesta = client.put(
        "/api/gobierno/contexto",
        json={"conectividad": "muy_buena"},
        headers={"Authorization": "Bearer x"},
    )

    assert respuesta.status_code == 422
    detalle = str(respuesta.json()["detail"]).lower()
    assert "estable" in detalle
    assert "intermitente" in detalle
    assert "sin_conexion" in detalle


def test_put_area_tic_existe_con_tipo_incorrecto_devuelve_422() -> None:
    _autenticar(uuid4())
    _con_sesion(None)

    respuesta = client.put(
        "/api/gobierno/contexto",
        json={"area_tic_existe": "tal_vez"},
        headers={"Authorization": "Bearer x"},
    )

    assert respuesta.status_code == 422

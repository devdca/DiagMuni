"""Tests HTTP (TestClient) de GET/PUT /api/gobierno/contexto (backend/app/api/
gobierno_contexto.py). Mismo enfoque que test_api_asistente_captura.py:
`TestClient` real sobre `app.main.app` con `dependency_overrides` de
`get_current_token`/`get_db`, sin Postgres real -- el router solo hace
`db.execute(select(...))`, `db.add`, `db.commit`, `db.refresh`, todo reproducible
con una sesión doble en memoria.

Al final del archivo hay un test de integración distinto de los de arriba: ejercita
`guardar_contexto` completo contra Postgres real (RLS incluido), no una sesión
doble -- la sesión doble de arriba tiene `refresh()` como no-op, así que nunca
hubiera detectado que `db.commit()` sin refijar el contexto de tenant rompe el
`db.refresh(fila)` real que le sigue (mismo patrón ya visto en
test_api_seguimiento.py/test_api_diagnosticos.py/test_plan_job.py)."""

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
    suficiente para ejercitar `_obtener_fila`/`guardar_contexto` sin Postgres.
    `execute` acepta `_params` opcional porque `guardar_contexto` ya llama al
    `fijar_contexto_tenant` real (no mockeado) tras su `db.commit()` -- ver
    app/db/rls.py::fijar_contexto_tenant, que pasa un dict de parámetros."""

    def __init__(self, fila: ContextoInstitucional | None = None) -> None:
        self.fila = fila
        self.agregados: list[object] = []
        self.commits = 0

    def execute(self, _stmt: object, _params: object = None) -> _ResultadoFalso:
        return _ResultadoFalso(self.fila)

    def add(self, obj: ContextoInstitucional) -> None:
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


# === PUT contra Postgres real (RLS incluido) ========================================


def _postgres_real_disponible() -> bool:
    import socket
    from urllib.parse import urlparse

    from app.core.config import settings
    from app.db.rls import abrir_sesion_tenant

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


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_put_no_revienta_rls_tras_commit_contra_postgres_real() -> None:
    from sqlalchemy import text

    from app.api.gobierno_contexto import guardar_contexto, obtener_contexto
    from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
    from app.models import Tenant
    from app.schemas.gobierno_contexto import ContextoInstitucionalIn

    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant de prueba contexto", clave=f"prueba-ctx-{tenant_id}", pais="mx"))
        db.commit()
        fijar_contexto_tenant(db, tenant_id)

        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        payload = ContextoInstitucionalIn(poblacion_total=50000, conectividad="estable")

        resultado = guardar_contexto(payload, token, db)
        assert resultado.poblacion_total == 50000
        assert resultado.conectividad == "estable"

        # La consulta real que antes revienta: después del `db.commit()` interno de
        # `guardar_contexto`, una consulta con RLS en la misma sesión debe seguir
        # funcionando -- acá, un GET real inmediatamente después del PUT.
        releido = obtener_contexto(token, db)
        assert releido.poblacion_total == 50000
    finally:
        try:
            db.execute(text("DELETE FROM contexto_institucional WHERE tenant_id = :t"), {"t": str(tenant_id)})
            db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

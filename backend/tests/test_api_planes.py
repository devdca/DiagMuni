"""Test de `_construir_plan_out` (backend/app/api/planes.py), la función pura que
arma el `PlanOut` de respuesta con el `indice_madurez` tomado del diagnóstico ya
cargado -- `PlanModernizacion` no tiene ese dato (sin relationship ORM hacia
`DiagnosticoTramite`, ver backend/app/models/plan_modernizacion.py).

No se testea el endpoint completo con `TestClient`: `obtener_plan_vigente` hace
varias consultas `db.execute(select(...))` (watchdog, diagnóstico, plan) antes de
llegar a esta función, y no existe infraestructura de DB real en este repo para
esos casos (mismo criterio ya documentado en test_plan_job.py). La parte con
lógica propia de esta tarea -- construir la respuesta -- es pura y se testea
directo, sin necesidad de esa infraestructura.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.adaptadores.http.deps import TokenData, get_current_token, get_db
from app.adaptadores.http.planes import _construir_plan_out
from app.main import app
from app.models import DiagnosticoTramite, PlanModernizacion, Tenant, Tramite

# Con las 4 claves ya presentes, `_contenido_con_faltantes` (app/adaptadores/
# http/planes.py) es un no-op -- estos tests siguen probando solo lo suyo
# (indice_madurez, progreso_historico), no la ruta de completar planes viejos
# (esa tiene su propia cobertura, ver test_contenido_con_faltantes más abajo).
_CONTENIDO_DE_PRUEBA = {
    "resumen_narrativo": "resumen",
    "brechas": [],
    "resumen_inversion": None,
    "resumen_personal": None,
    "orden_sugerido": None,
    "estimacion_recursos": None,
}


def _plan_de_prueba(**overrides: object) -> PlanModernizacion:
    base: dict[str, object] = {
        "id": uuid4(),
        "diagnostico_tramite_id": uuid4(),
        "tenant_id": uuid4(),
        "version": 1,
        "modo": "degradado",
        "contenido": _CONTENIDO_DE_PRUEBA,
        "verificado": True,
        "generado_en": datetime.now(UTC),
    }
    base.update(overrides)
    return PlanModernizacion(**base)


def _token_de_prueba(tenant_id: object) -> TokenData:
    return TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")  # type: ignore[arg-type]


def _tramite_y_tenant_de_prueba(tenant_id: object) -> tuple[Tramite, Tenant]:
    tramite = Tramite(tenant_id=tenant_id, nombre="Trámite", estado="plan_listo", tipo="generico")  # type: ignore[arg-type]
    tenant = Tenant(id=tenant_id, nombre="Gobierno de prueba", clave="prueba", pais="mx")  # type: ignore[arg-type]
    return tramite, tenant


class _SesionNoUsada:
    """`_progreso_historico_de` no debe consultar la DB cuando `version <= 1` --
    esta sesión revienta si algo intenta usarla vía `execute`, para que un cambio
    futuro que rompa ese corto-circuito falle ruidosamente en el test, no en
    producción. `_construir_plan_out` sí necesita `get()` incondicionalmente
    (resuelve Tramite/Tenant) -- eso no está bajo prueba acá, se sirve fijo."""

    def __init__(self, tramite: Tramite, tenant: Tenant) -> None:
        self._tramite = tramite
        self._tenant = tenant

    def get(self, modelo: type, _id: object) -> object:
        if modelo is Tramite:
            return self._tramite
        if modelo is Tenant:
            return self._tenant
        raise AssertionError(f"get inesperado: {modelo}")

    def execute(self, *_args: object, **_kwargs: object) -> object:
        raise AssertionError("no debería consultarse la DB cuando plan.version <= 1")


class _ResultadoFalso:
    def __init__(self, valor: object) -> None:
        self._valor = valor

    def scalar_one_or_none(self) -> object:
        return self._valor


class _SesionConPlanAnterior:
    def __init__(self, tramite: Tramite, tenant: Tenant, plan_anterior: PlanModernizacion | None) -> None:
        self._tramite = tramite
        self._tenant = tenant
        self._plan_anterior = plan_anterior

    def get(self, modelo: type, _id: object) -> object:
        if modelo is Tramite:
            return self._tramite
        if modelo is Tenant:
            return self._tenant
        raise AssertionError(f"get inesperado: {modelo}")

    def execute(self, *_args: object, **_kwargs: object) -> _ResultadoFalso:
        return _ResultadoFalso(self._plan_anterior)


def test_construir_plan_out_incluye_indice_de_madurez_del_diagnostico() -> None:
    tenant_id = uuid4()
    diagnostico = DiagnosticoTramite(tenant_id=tenant_id, tramite_id=uuid4(), respuestas={}, indice_madurez=2)
    plan = _plan_de_prueba(tenant_id=tenant_id)
    tramite, tenant = _tramite_y_tenant_de_prueba(tenant_id)

    resultado = _construir_plan_out(plan, diagnostico, _token_de_prueba(tenant_id), _SesionNoUsada(tramite, tenant))

    assert resultado.indice_madurez == 2
    assert resultado.modo == "degradado"
    assert resultado.contenido == _CONTENIDO_DE_PRUEBA
    assert resultado.verificado is True


def test_construir_plan_out_admite_indice_madurez_none() -> None:
    """Estado no alcanzable hoy a través del flujo real de la API: `enviar_diagnostico`
    (backend/app/api/diagnosticos.py) siempre fija `indice_madurez` de forma síncrona
    antes de disparar el job que genera el plan, así que en la práctica nunca existe
    un plan sin que el diagnóstico ya tenga índice. La columna sí es `nullable=True`
    (backend/app/models/diagnostico_tramite.py) -- el schema no debe reventar si
    ese dato faltara por cualquier otra vía (ej. manipulación directa de datos)."""
    tenant_id = uuid4()
    diagnostico = DiagnosticoTramite(tenant_id=tenant_id, tramite_id=uuid4(), respuestas={}, indice_madurez=None)
    plan = _plan_de_prueba(tenant_id=tenant_id)
    tramite, tenant = _tramite_y_tenant_de_prueba(tenant_id)

    resultado = _construir_plan_out(plan, diagnostico, _token_de_prueba(tenant_id), _SesionNoUsada(tramite, tenant))

    assert resultado.indice_madurez is None


def test_construir_plan_out_version_1_no_tiene_progreso_historico() -> None:
    tenant_id = uuid4()
    diagnostico = DiagnosticoTramite(tenant_id=tenant_id, tramite_id=uuid4(), respuestas={}, indice_madurez=2)
    plan = _plan_de_prueba(tenant_id=tenant_id, version=1)
    tramite, tenant = _tramite_y_tenant_de_prueba(tenant_id)

    resultado = _construir_plan_out(plan, diagnostico, _token_de_prueba(tenant_id), _SesionNoUsada(tramite, tenant))

    assert resultado.progreso_historico is None


def test_construir_plan_out_version_2_calcula_progreso_contra_la_version_anterior() -> None:
    tenant_id = uuid4()
    diagnostico = DiagnosticoTramite(tenant_id=tenant_id, tramite_id=uuid4(), respuestas={}, indice_madurez=3)
    diagnostico_tramite_id = uuid4()
    contenido_anterior = {
        "resumen_narrativo": "r",
        "brechas": [{"variable": "motor_pagos"}, {"variable": "interoperabilidad"}],
        "resumen_inversion": None,
        "resumen_personal": None,
        "orden_sugerido": None,
        "estimacion_recursos": None,
    }
    contenido_actual = {
        "resumen_narrativo": "r",
        "brechas": [{"variable": "interoperabilidad"}, {"variable": "version_accesible"}],
        "resumen_inversion": None,
        "resumen_personal": None,
        "orden_sugerido": None,
        "estimacion_recursos": None,
    }
    plan_anterior = _plan_de_prueba(
        tenant_id=tenant_id, diagnostico_tramite_id=diagnostico_tramite_id, version=1, contenido=contenido_anterior
    )
    plan = _plan_de_prueba(
        tenant_id=tenant_id, diagnostico_tramite_id=diagnostico_tramite_id, version=2, contenido=contenido_actual
    )
    tramite, tenant = _tramite_y_tenant_de_prueba(tenant_id)

    resultado = _construir_plan_out(
        plan, diagnostico, _token_de_prueba(tenant_id), _SesionConPlanAnterior(tramite, tenant, plan_anterior)
    )

    assert resultado.progreso_historico == {
        "brechas_resueltas": ["motor_pagos"],
        "brechas_nuevas": ["version_accesible"],
        "brechas_persistentes": ["interoperabilidad"],
    }


def test_construir_plan_out_version_2_sin_fila_anterior_encontrada_no_falla() -> None:
    # Caso de borde defensivo: version > 1 pero la fila anterior no se encuentra
    # (no debería ocurrir en la práctica, las versiones nunca se borran) -- debe
    # degradar a None, nunca lanzar.
    tenant_id = uuid4()
    diagnostico = DiagnosticoTramite(tenant_id=tenant_id, tramite_id=uuid4(), respuestas={}, indice_madurez=3)
    plan = _plan_de_prueba(tenant_id=tenant_id, version=2)
    tramite, tenant = _tramite_y_tenant_de_prueba(tenant_id)

    resultado = _construir_plan_out(
        plan, diagnostico, _token_de_prueba(tenant_id), _SesionConPlanAnterior(tramite, tenant, None)
    )

    assert resultado.progreso_historico is None


# === GET .../plan/pdf -- TestClient, sesión doble en memoria =======================

_CONTENIDO_PDF_PRUEBA = {
    "resumen_narrativo": "resumen de prueba",
    "brechas": [],
    "sugerencia_libre": None,
    "resumen_inversion": {
        "moneda_local_codigo": "MXN",
        "inversion_unica_estimada": {"moneda_local": None, "usd": None},
        "costo_recurrente_mensual_estimado": {"moneda_local": None, "usd": None},
        "componentes": [],
        "brechas_totales": 0,
        "brechas_con_componente_software": 0,
        "nota_cobertura": "nota",
    },
    "resumen_personal": {
        "acciones_organizacionales": [],
        "personal_ti_actual": None,
        "personal_total_gobierno": None,
        "capacitacion_anual_vigente": None,
        "costo_referencia_personal_ti": None,
    },
    "orden_sugerido": {"sin_prerrequisitos": [], "con_prerrequisitos": []},
    "estimacion_recursos": None,
}


class _SesionFalsaPlanPdf:
    """Doble de `Session` para `descargar_plan_pdf`/`obtener_plan_vigente` -- un
    `db.get()` por modelo (Tramite/Tenant) y un `db.execute(select(...))` por
    tabla (DiagnosticoTramite/PlanModernizacion), distinguidos por el texto SQL
    compilado, mismo criterio que `_SesionCompleta` en test_plan_job.py."""

    def __init__(self, tramite: Tramite, tenant: Tenant, diagnostico: DiagnosticoTramite, plan: PlanModernizacion):
        self._tramite = tramite
        self._tenant = tenant
        self._diagnostico = diagnostico
        self._plan = plan

    def get(self, modelo: type, _id: object) -> object:
        if modelo is Tramite:
            return self._tramite
        if modelo is Tenant:
            return self._tenant
        raise AssertionError(f"get inesperado: {modelo}")

    def execute(self, stmt: object) -> "_ResultadoFalso":
        # "plan_modernizacion" primero: la columna FK diagnostico_tramite_id hace
        # que el SELECT de PlanModernizacion también contenga la substring
        # "diagnostico_tramite", así que ese chequeo debe ir después.
        texto = str(stmt)
        if "FROM plan_modernizacion" in texto:
            return _ResultadoFalso(self._plan)
        if "FROM diagnostico_tramite" in texto:
            return _ResultadoFalso(self._diagnostico)
        raise AssertionError(f"execute inesperado: {texto}")


@pytest.fixture(autouse=True)
def _limpiar_overrides():
    yield
    app.dependency_overrides.clear()


def _autenticar_y_sesion(sesion: _SesionFalsaPlanPdf, tenant_id: object) -> None:
    app.dependency_overrides[get_current_token] = lambda: TokenData(
        usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario"
    )
    app.dependency_overrides[get_db] = lambda: sesion


def test_descargar_plan_pdf_sin_plan_devuelve_404() -> None:
    tenant_id = uuid4()
    tramite = Tramite(id=uuid4(), tenant_id=tenant_id, nombre="Trámite", estado="en_progreso", tipo="generico")
    tenant = Tenant(id=tenant_id, nombre="Gobierno de prueba", clave="prueba", pais="mx")
    sesion = _SesionFalsaPlanPdf(tramite, tenant, diagnostico=None, plan=None)  # type: ignore[arg-type]
    _autenticar_y_sesion(sesion, tenant_id)
    client = TestClient(app)

    respuesta = client.get(f"/api/tramites/{tramite.id}/plan/pdf", headers={"Authorization": "Bearer x"})

    assert respuesta.status_code == 404


def test_descargar_plan_pdf_con_plan_devuelve_pdf_descargable() -> None:
    tenant_id = uuid4()
    tramite_id = uuid4()
    diagnostico_id = uuid4()
    tramite = Tramite(id=tramite_id, tenant_id=tenant_id, nombre="Trámite", estado="plan_listo", tipo="generico")
    tenant = Tenant(id=tenant_id, nombre="Gobierno de prueba", clave="prueba", pais="mx")
    diagnostico = DiagnosticoTramite(
        id=diagnostico_id, tenant_id=tenant_id, tramite_id=tramite_id, respuestas={}, indice_madurez=2
    )
    plan = PlanModernizacion(
        id=uuid4(),
        diagnostico_tramite_id=diagnostico_id,
        tenant_id=tenant_id,
        version=1,
        modo="degradado",
        contenido=_CONTENIDO_PDF_PRUEBA,
        verificado=True,
        generado_en=datetime.now(UTC),
    )
    sesion = _SesionFalsaPlanPdf(tramite, tenant, diagnostico, plan)
    _autenticar_y_sesion(sesion, tenant_id)
    client = TestClient(app)

    respuesta = client.get(f"/api/tramites/{tramite_id}/plan/pdf", headers={"Authorization": "Bearer x"})

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert "attachment" in respuesta.headers["content-disposition"]
    assert respuesta.content.startswith(b"%PDF")

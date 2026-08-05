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

from app.api.planes import _construir_plan_out
from app.models import DiagnosticoTramite, PlanModernizacion

_CONTENIDO_DE_PRUEBA = {"resumen_narrativo": "resumen", "brechas": []}


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


def test_construir_plan_out_incluye_indice_de_madurez_del_diagnostico() -> None:
    diagnostico = DiagnosticoTramite(tenant_id=uuid4(), tramite_id=uuid4(), respuestas={}, indice_madurez=2)
    plan = _plan_de_prueba()

    resultado = _construir_plan_out(plan, diagnostico)

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
    diagnostico = DiagnosticoTramite(tenant_id=uuid4(), tramite_id=uuid4(), respuestas={}, indice_madurez=None)
    plan = _plan_de_prueba()

    resultado = _construir_plan_out(plan, diagnostico)

    assert resultado.indice_madurez is None

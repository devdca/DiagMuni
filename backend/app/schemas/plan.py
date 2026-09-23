from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PlanOut(BaseModel):
    id: UUID
    diagnostico_tramite_id: UUID
    version: int
    modo: str
    contenido: dict
    verificado: bool
    generado_en: datetime
    # No vive en `PlanModernizacion` (sin relationship a `DiagnosticoTramite`,
    # ver backend/app/models/plan_modernizacion.py) -- quien construye este
    # schema debe fijarlo explícitamente desde el diagnóstico ya cargado.
    indice_madurez: int | None = None
    # Diff determinista contra la versión anterior del mismo diagnóstico
    # (app/engine/resumen_plan.py::calcular_progreso_historico) -- `None` cuando
    # esta es la primera versión (no hay con qué comparar), calculado en lectura,
    # nunca persistido en `contenido` (depende de dos filas a la vez).
    progreso_historico: dict | None = None

    model_config = {"from_attributes": True}


class VersionPlanResumen(BaseModel):
    """Una fila del selector del comparador de versiones (frontend) -- nunca el
    `contenido` completo, sería pesado para una lista."""

    version: int
    modo: str
    verificado: bool
    generado_en: datetime
    brechas_totales: int


class PlanVersionDetalleOut(BaseModel):
    """Detalle completo de UNA versión específica del plan -- a diferencia de
    `PlanOut` (siempre la vigente), esta puede ser cualquier versión histórica.
    Sin `indice_madurez`: `diagnostico_tramite` solo guarda el índice ACTUAL, no
    uno por versión de plan -- mostrarlo aquí sugeriría un historial que no existe."""

    version: int
    modo: str
    verificado: bool
    generado_en: datetime
    contenido: dict

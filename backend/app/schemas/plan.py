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

    model_config = {"from_attributes": True}

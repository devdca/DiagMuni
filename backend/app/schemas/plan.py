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

    model_config = {"from_attributes": True}

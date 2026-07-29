from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class AccionSeguimientoOut(BaseModel):
    id: UUID
    plan_modernizacion_id: UUID
    descripcion: str
    responsable: str
    fecha_objetivo: date
    estado_semaforo: str
    actualizado_en: datetime

    model_config = {"from_attributes": True}


class AccionSeguimientoActualizarEstado(BaseModel):
    estado_semaforo: str

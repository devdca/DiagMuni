from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CrearNotaRequest(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)


class NotaSeguimientoOut(BaseModel):
    id: UUID
    accion_seguimiento_id: UUID
    usuario_id: UUID
    usuario_nombre: str
    texto: str
    creado_en: datetime

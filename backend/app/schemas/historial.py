from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EventoHistorialOut(BaseModel):
    id: UUID
    tipo: str
    descripcion: str
    usuario_id: UUID | None
    metadatos: dict | None
    creado_en: datetime

    model_config = {"from_attributes": True}

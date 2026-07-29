from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TramiteCreate(BaseModel):
    nombre: str
    descripcion: str = ""


class TramiteOut(BaseModel):
    id: UUID
    nombre: str
    descripcion: str
    estado: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

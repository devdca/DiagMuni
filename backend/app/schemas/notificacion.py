from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotificacionOut(BaseModel):
    id: UUID
    tipo: str
    titulo: str
    mensaje: str
    tramite_id: UUID | None
    leida: bool
    creado_en: datetime

    model_config = {"from_attributes": True}


class ListaNotificacionesOut(BaseModel):
    notificaciones: list[NotificacionOut]
    no_leidas: int

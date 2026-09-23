import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class EventoHistorial(Base):
    """RLS por tenant_id. Bitácora persistida por trámite (migración 0012) --
    alimenta la pestaña "Historial" del detalle de un trámite. `tipo` es texto
    libre (ver constantes en app/aplicacion/historial.py), no un enum de Postgres."""

    __tablename__ = "evento_historial"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    tramite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tramite.id", ondelete="CASCADE"), nullable=False
    )
    # Sin FK a `usuario` a propósito -- ver migración 0012 para el porqué.
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[str] = mapped_column(String, nullable=False)
    metadatos: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())

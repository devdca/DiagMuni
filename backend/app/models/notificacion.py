import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Notificacion(Base):
    """RLS por tenant_id (migración 0013). Tenant-wide: sin destinatario individual
    ni lectura por usuario en esta primera versión (ver docstring de la migración)."""

    __tablename__ = "notificacion"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    tramite_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tramite.id", ondelete="CASCADE"), nullable=True
    )
    # Solo se llena para tipo="accion_atrasada" -- ver migración 0013 para el porqué.
    accion_seguimiento_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accion_seguimiento.id", ondelete="CASCADE"), nullable=True
    )
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    titulo: Mapped[str] = mapped_column(String, nullable=False)
    mensaje: Mapped[str] = mapped_column(String, nullable=False)
    leida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())

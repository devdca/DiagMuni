import uuid
from datetime import date, datetime
from typing import Literal

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class AccionSeguimiento(Base):
    """RLS por tenant_id, denormalizado. 3 estados de semáforo (docs/ux-brief.md)."""

    __tablename__ = "accion_seguimiento"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_modernizacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plan_modernizacion.id"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    descripcion: Mapped[str] = mapped_column(String, nullable=False)
    responsable: Mapped[str] = mapped_column(String, nullable=False)
    fecha_objetivo: Mapped[date] = mapped_column(Date, nullable=False)
    estado_semaforo: Mapped[Literal["completado", "en_progreso", "atrasado"]] = mapped_column(
        Enum("completado", "en_progreso", "atrasado", name="estado_semaforo_enum"),
        nullable=False,
        default="en_progreso",
    )
    actualizado_en: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

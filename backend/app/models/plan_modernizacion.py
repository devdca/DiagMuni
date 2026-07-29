import uuid
from datetime import datetime

from sqlalchemy import Boolean, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class PlanModernizacion(Base):
    """RLS por tenant_id, denormalizado. version incrementa si se regenera; versiones
    previas nunca se borran (docs/backend-schema.md, docs/app-flow.md)."""

    __tablename__ = "plan_modernizacion"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    diagnostico_tramite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diagnostico_tramite.id"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    modo: Mapped[str] = mapped_column(Enum("llm", "degradado", name="modo_plan_enum"), nullable=False)
    contenido: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # false bloquea la vista y reintenta — nunca se muestra un plan no verificado (docs/backend-schema.md).
    verificado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    generado_en: Mapped[datetime] = mapped_column(server_default=func.now())

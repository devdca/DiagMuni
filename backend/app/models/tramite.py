import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base

ESTADOS_TRAMITE = ("sin_iniciar", "en_progreso", "diagnosticado", "generando_plan", "plan_listo")


class Tramite(Base):
    """RLS por tenant_id. Estados = máquina de estados de docs/app-flow.md."""

    __tablename__ = "tramite"
    __table_args__ = (UniqueConstraint("tenant_id", "nombre", name="uq_tramite_tenant_nombre"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[str] = mapped_column(String, nullable=False, default="")
    estado: Mapped[str] = mapped_column(
        Enum(*ESTADOS_TRAMITE, name="estado_tramite_enum"), nullable=False, default="sin_iniciar"
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

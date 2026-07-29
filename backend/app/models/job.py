import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, SmallInteger
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Job(Base):
    """RLS por tenant_id. Ciclo de vida en docs/TRD.md, "Job asíncrono"."""

    __tablename__ = "job"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(Enum("generacion_plan", name="tipo_job_enum"), nullable=False)
    diagnostico_tramite_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diagnostico_tramite.id"), nullable=True
    )
    estado: Mapped[str] = mapped_column(
        Enum("pending", "running", "done", "failed", name="estado_job_enum"), nullable=False, default="pending"
    )
    intentos: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    resultado: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

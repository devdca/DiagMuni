import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class DiagnosticoTramite(Base):
    """RLS por tenant_id, denormalizado a propósito (no depender de un join a tramite
    para la policy) — docs/backend-schema.md."""

    __tablename__ = "diagnostico_tramite"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tramite_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tramite.id"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    respuestas: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    indice_madurez: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    version_motor: Mapped[str | None] = mapped_column(String, nullable=True)
    completado_en: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

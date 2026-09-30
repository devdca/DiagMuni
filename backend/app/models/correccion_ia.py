import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class CorreccionIa(Base):
    """RLS por tenant_id (migración 0020) -- bitácora append-only de correcciones
    humanas sobre salidas de la capa de IA (ver docstring de la migración para el
    diseño completo: RAG + evaluación, nunca reentrenamiento). Nunca se edita ni
    se borra una fila ya escrita."""

    __tablename__ = "correccion_ia"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    tramite_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tramite.id", ondelete="CASCADE"), nullable=True
    )
    pieza: Mapped[str] = mapped_column(String, nullable=False)
    entrada_llm: Mapped[str] = mapped_column(Text, nullable=False)
    salida_llm: Mapped[str] = mapped_column(Text, nullable=False)
    correccion: Mapped[str] = mapped_column(Text, nullable=False)
    ruta_llm: Mapped[str | None] = mapped_column(String, nullable=True)
    creado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id"), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())

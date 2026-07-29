import uuid
from datetime import datetime

from sqlalchemy import Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Tenant(Base):
    """Tabla raíz de aislamiento multi-tenant — sin RLS propio (docs/backend-schema.md)."""

    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    pais: Mapped[str] = mapped_column(Enum("mx", "uy", name="pais_enum"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

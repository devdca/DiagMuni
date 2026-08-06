import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ContextoInstitucional(Base):
    """Perfil de contexto y capacidad institucional del gobierno, 1:1 con tenant
    (entregables/fase-2/variables-contexto-institucional.md, sección 4). RLS por
    tenant_id igual que el resto de tablas de negocio -- ver
    backend/alembic/versions/0003_contexto_institucional.py. Todas las columnas de
    negocio son nullable y editables en cualquier momento, sin excepción."""

    __tablename__ = "contexto_institucional"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False, unique=True
    )
    poblacion_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    personal_total_gobierno: Mapped[int | None] = mapped_column(Integer, nullable=True)
    presupuesto_tic_anual: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    area_tic_existe: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    conectividad: Mapped[str | None] = mapped_column(
        Enum("estable", "intermitente", "sin_conexion", name="conectividad_enum"), nullable=True
    )
    normativa_local_emitida: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Única de las 7 variables de contexto/capacidad institucional con
    # criterio_deteccion real en engine/reglas/ (ver
    # backend/app/engine/reglas/autoridad_gobernanza_digital.yaml).
    autoridad_gobernanza_digital: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    actualizado_en: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class HistorialIndiceGlobal(Base):
    """RLS por tenant_id. Un punto por cada vez que se envía/corrige un
    diagnóstico (migración 0015) -- alimenta la gráfica de tendencia real del
    Panel de control. Append-only: nunca se actualiza ni se borra un punto ya
    escrito, mismo criterio que EventoHistorial.

    `nivel_N_conteo` (migración 0016): cuántos trámites activos estaban en
    cada nivel de la rampa (0-4) en el mismo instante del snapshot -- para la
    gráfica apilada por nivel, no solo el promedio."""

    __tablename__ = "historial_indice_global"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    indice_global: Mapped[float] = mapped_column(Float, nullable=False)
    nivel_0_conteo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nivel_1_conteo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nivel_2_conteo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nivel_3_conteo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nivel_4_conteo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())

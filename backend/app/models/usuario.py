import uuid
from datetime import datetime

from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base

# admin_gobierno: gestiona usuarios/catálogo/salud de IA. funcionario: diagnósticos y planes.
ROLES_VALIDOS = ("funcionario", "admin_gobierno")


class Usuario(Base):
    """RLS por tenant_id (docs/backend-schema.md)."""

    __tablename__ = "usuario"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_usuario_tenant_email"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    rol: Mapped[str] = mapped_column(
        Enum(*ROLES_VALIDOS, name="rol_enum"), nullable=False, default="funcionario"
    )
    # Rechazado en cada request, no solo en login.
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ultimo_login_en: Mapped[datetime | None] = mapped_column(nullable=True)  # NULL = nunca inició sesión
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

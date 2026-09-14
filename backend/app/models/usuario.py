import uuid
from datetime import datetime

from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base

# Dos roles (migración 0011, RBAC): `admin_gobierno` gestiona usuarios, catálogo
# de trámites y salud del sistema de IA (app/adaptadores/http/admin_usuarios.py);
# `funcionario` responde diagnósticos y ve planes. Ya no es el "un solo rol en
# el MVP" que docs/backend-schema.md listaba como riesgo abierto.
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
    # Alta/baja reversible de un funcionario (antes solo posible tocando la base de
    # datos a mano) -- `get_current_token` (app/adaptadores/http/deps.py) rechaza
    # todo token de un usuario inactivo en cada request, no solo en el login.
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # `NULL` = nunca inició sesión. Se actualiza en cada login exitoso
    # (app/adaptadores/http/auth.py) -- visible en el panel de administración para
    # distinguir una cuenta inactiva de una que nunca se usó.
    ultimo_login_en: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

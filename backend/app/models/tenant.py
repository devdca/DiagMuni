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
    # Id corto del login, normalizado en capa de app.
    clave: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    pais: Mapped[str] = mapped_column(Enum("mx", "uy", name="pais_enum"), nullable=False)
    # CHECK constraint (no Enum nativo, migración 0018). `default` de Python además
    # del `server_default`: un Tenant en memoria sin este campo (tests, CLI) queda
    # en "municipal" de inmediato, sin esperar flush/commit.
    nivel_gobierno: Mapped[str] = mapped_column(String, nullable=False, default="municipal", server_default="municipal")

    # Clave geoestadística INEGI (5 dígitos). Nullable: sin ella, la sincronización
    # con INEGI simplemente no aplica (no aplica tampoco a nivel_gobierno="federal").
    clave_geoestadistica: Mapped[str | None] = mapped_column(String(5), nullable=True)

    # BYOK: cada gobierno trae y paga su propia credencial de IA. NULL =
    # comportamiento global (autodetect de LLM_PROVIDER).
    proveedor_llm_preferido: Mapped[str | None] = mapped_column(String, nullable=True)
    deepseek_api_key_cifrada: Mapped[str | None] = mapped_column(String, nullable=True)  # Fernet, nunca texto plano
    anthropic_api_key_cifrada: Mapped[str | None] = mapped_column(String, nullable=True)
    ollama_api_base: Mapped[str | None] = mapped_column(String, nullable=True)  # no es secreto, no se cifra

    # Logo del gobierno: el archivo vive en disco (logo_storage.py), acá solo el
    # tipo MIME y cuándo se actualizó (el frontend lo usa para invalidar su
    # caché). Ambos NULL = sin logo, la UI cae a mostrar `nombre`.
    logo_content_type: Mapped[str | None] = mapped_column(String, nullable=True)
    logo_actualizado_en: Mapped[datetime | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

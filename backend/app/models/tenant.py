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
    # Identificador corto y legible que el funcionario escribe en el login para
    # identificar a su gobierno (entregables/fase-2/identificacion-gobierno-login.md,
    # sección 1) — normalizado (trim + minúsculas) en capa de aplicación, no acá.
    clave: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    pais: Mapped[str] = mapped_column(Enum("mx", "uy", name="pais_enum"), nullable=False)
    # Ortogonal a `pais` (migración 0018, ver docstring) -- CHECK constraint,
    # no Enum nativo, mismo motivo que `proveedor_llm_preferido` abajo.
    # `default` (Python) además de `server_default` (DB): un `Tenant(...)`
    # construido en memoria sin pasar `nivel_gobierno` (ej. en tests, o en
    # `crear_gobierno` con el parámetro por defecto) debe quedar en
    # "municipal" de inmediato, no solo al hacer flush/commit contra la BD.
    nivel_gobierno: Mapped[str] = mapped_column(String, nullable=False, default="municipal", server_default="municipal")

    # Clave geoestadística INEGI de 5 dígitos (2 entidad + 3 municipio, ej.
    # "09004" = Cuajimalpa de Morelos) -- migración 0019. Nullable: sin ella,
    # app/adaptadores/inegi/cliente_inegi.py simplemente no puede sincronizar
    # (cierra de forma segura, ver ese módulo), y no aplica a nivel_gobierno="federal".
    clave_geoestadistica: Mapped[str | None] = mapped_column(String(5), nullable=True)

    # BYOK (bring your own key, ver migración 0016): cada gobierno trae y paga su
    # propia credencial de IA -- en el despliegue real el operador no deja ninguna
    # key propia configurada. NULL = el tenant no configuró nada todavía (para
    # `proveedor_llm_preferido`, NULL además significa "usar el comportamiento
    # global de LLM_PROVIDER/autodetect", ver app/adaptadores/llm/config.py).
    proveedor_llm_preferido: Mapped[str | None] = mapped_column(String, nullable=True)
    # Cifradas con Fernet (app/core/cifrado.py) usando TENANT_SECRET_KEY -- nunca
    # texto plano, nunca se devuelven en claro por la API una vez guardadas.
    deepseek_api_key_cifrada: Mapped[str | None] = mapped_column(String, nullable=True)
    anthropic_api_key_cifrada: Mapped[str | None] = mapped_column(String, nullable=True)
    # URL del propio servidor Ollama del tenant -- no es secreto, no se cifra.
    ollama_api_base: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

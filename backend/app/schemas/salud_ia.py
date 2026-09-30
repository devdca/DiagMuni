from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PlanRecienteOut(BaseModel):
    tramite_id: UUID
    tramite_nombre: str
    version: int
    modo: str
    verificado: bool
    generado_en: datetime


class ResumenSaludIaOut(BaseModel):
    """Estado del sistema de IA para el panel de administración -- todo derivado
    de columnas que ya existen (`plan_modernizacion`, `job`), nunca una métrica
    nueva que requiera instrumentación aparte (docs/TRD.md, "Observabilidad":
    sin stack pesado para el MVP).

    BYOK (app/core/cifrado.py, migración 0016): `proveedor_activo` ya incluye el
    override de este tenant si configuró uno (ver
    app/aplicacion/preferencia_modelo_ia.py::resolver_proveedor_activo).
    `deepseek_key_configurada`/`anthropic_key_configurada` son booleanos a
    propósito -- las credenciales cifradas NUNCA se devuelven en claro por la
    API una vez guardadas, ni siquiera a un admin_gobierno del propio tenant."""

    proveedor_activo: str | None
    proveedor_preferido: str | None
    proveedores_disponibles: list[str]
    deepseek_key_configurada: bool
    anthropic_key_configurada: bool
    ollama_api_base: str | None
    ultimo_plan: PlanRecienteOut | None
    jobs_fallidos_24h: int
    planes_recientes: list[PlanRecienteOut]


class ActualizarProveedorLlmRequest(BaseModel):
    """Upsert parcial (mismo criterio que `ContextoInstitucionalIn` en
    gobierno_contexto.py, vía `model_dump(exclude_unset=True)`): un campo
    OMITIDO no toca el valor guardado; un campo enviado como `""`/`None` borra
    la credencial/preferencia guardada (mismo criterio que `api_key_de`: vacío
    cuenta como ausente)."""

    proveedor: str | None = None
    deepseek_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_api_base: str | None = None

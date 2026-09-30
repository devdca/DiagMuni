"""Preferencia y credenciales de IA por gobierno (BYOK, ver migración 0016 y
app/core/cifrado.py) -- config operativa administrativa (afecta costo de la
API de IA), no un dato de diagnóstico, por eso vive junto a `Tenant` y no en
`ContextoInstitucional`. Llamado desde app/adaptadores/http/admin_salud_ia.py
(requiere admin_gobierno, ver deps.py::requerir_admin) para leer/escribir, y
desde cada punto de la capa de IA que arma un `OverrideLlmTenant` una sola vez
por request/job (ver `resolver_override`)."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.adaptadores.llm.config import OverrideLlmTenant, obtener_proveedor_llm, proveedores_soportados
from app.core.cifrado import cifrar, descifrar
from app.models import Tenant


def resolver_override(tenant: Tenant | None) -> OverrideLlmTenant | None:
    """Arma el `OverrideLlmTenant` de un tenant ya cargado, descifrando sus
    credenciales guardadas -- se llama UNA vez por request/job (nunca dentro de
    un loop ni por cada intento de ruta) y el resultado se pasa hacia abajo por
    toda la cadena de llamada. `None` si no hay tenant (ej. no se pudo cargar),
    para que quien llama caiga limpio al comportamiento global existente."""
    if tenant is None:
        return None
    return OverrideLlmTenant(
        proveedor=tenant.proveedor_llm_preferido,
        deepseek_api_key=descifrar(tenant.deepseek_api_key_cifrada) if tenant.deepseek_api_key_cifrada else None,
        anthropic_api_key=descifrar(tenant.anthropic_api_key_cifrada) if tenant.anthropic_api_key_cifrada else None,
        ollama_api_base=tenant.ollama_api_base,
    )


def resolver_proveedor_activo(tenant: Tenant | None) -> str | None:
    return obtener_proveedor_llm(override=resolver_override(tenant))


def actualizar_preferencia(db: Session, *, tenant_id: UUID, cambios: dict) -> Tenant | None:
    """`cambios`: solo los campos presentes se tocan (upsert parcial, mismo
    criterio que `gobierno_contexto.py`) -- values de
    `ActualizarProveedorLlmRequest.model_dump(exclude_unset=True)`. Claves
    válidas: "proveedor", "deepseek_api_key", "anthropic_api_key",
    "ollama_api_base". Una key no vacía se cifra antes de guardarse; una key
    enviada como "" borra la credencial guardada (mismo criterio que
    `api_key_de`: vacío cuenta como ausente). `None` si el tenant no existe.
    `ValueError` si `proveedor` no es uno de los soportados (`None` en sí mismo
    siempre es válido -- significa "sin preferencia propia")."""
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        return None

    if "proveedor" in cambios:
        proveedor = cambios["proveedor"]
        if proveedor is not None:
            proveedor = proveedor.strip().lower()
            if proveedor and proveedor not in proveedores_soportados():
                raise ValueError(
                    f"Proveedor '{proveedor}' no soportado. Use uno de: {sorted(proveedores_soportados())}."
                )
            proveedor = proveedor or None
        tenant.proveedor_llm_preferido = proveedor

    if "deepseek_api_key" in cambios:
        valor = cambios["deepseek_api_key"]
        tenant.deepseek_api_key_cifrada = cifrar(valor) if valor else None

    if "anthropic_api_key" in cambios:
        valor = cambios["anthropic_api_key"]
        tenant.anthropic_api_key_cifrada = cifrar(valor) if valor else None

    if "ollama_api_base" in cambios:
        tenant.ollama_api_base = cambios["ollama_api_base"] or None

    db.flush()
    return tenant

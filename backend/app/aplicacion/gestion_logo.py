"""Valida y orquesta la subida del logo de un gobierno -- capa de aplicación,
sin conocer HTTP (mismo criterio que sincronizacion_inegi.py). La validación de
tipo/tamaño vive acá, no en el router, para que sea una sola fuente de verdad
reusable si en el futuro aparece un segundo camino de subida (ej. un script de
alta masiva de gobiernos)."""

from datetime import UTC, datetime

from app.adaptadores.almacenamiento import logo_storage
from app.core.config import settings
from app.models import Tenant

# Misma lista que el CHECK constraint de `tenant.logo_content_type`
# (alembic/versions/0021_tenant_logo.py) -- si se agrega un tipo acá, agregarlo
# también ahí (y viceversa), son la misma regla de negocio en dos capas.
TIPOS_LOGO_VALIDOS = ("image/png", "image/jpeg", "image/svg+xml")


class LogoInvalidoError(Exception):
    """Motivo legible de por qué se rechazó la subida -- el router HTTP la
    traduce a un 422, esta función solo decide el mensaje."""


def guardar_logo_tenant(tenant: Tenant, contenido: bytes, content_type: str | None) -> None:
    """Guarda `contenido` en disco y actualiza la metadata del tenant -- no hace
    `commit`, eso lo decide quien llama (mismo criterio que `sincronizar_poblacion`
    en sincronizacion_inegi.py)."""
    if content_type not in TIPOS_LOGO_VALIDOS:
        raise LogoInvalidoError(
            f"Tipo de archivo no permitido ({content_type or 'desconocido'}). "
            f"Usa uno de: {', '.join(TIPOS_LOGO_VALIDOS)}."
        )
    if len(contenido) == 0:
        raise LogoInvalidoError("El archivo está vacío.")
    if len(contenido) > settings.logo_max_bytes:
        limite_mb = settings.logo_max_bytes / (1024 * 1024)
        raise LogoInvalidoError(f"El archivo supera el límite de {limite_mb:.0f} MB.")

    logo_storage.guardar_logo(tenant.id, contenido)
    tenant.logo_content_type = content_type
    tenant.logo_actualizado_en = datetime.now(UTC)

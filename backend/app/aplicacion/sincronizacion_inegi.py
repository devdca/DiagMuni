"""Orquesta la sincronización de `poblacion_total` contra la API de INEGI
(app/adaptadores/inegi/cliente_inegi.py) para un tenant -- capa de aplicación,
sin conocer HTTP (igual que preferencia_modelo_ia.py). El dato de INEGI nunca
sobreescribe en silencio: se guarda con `poblacion_total_fuente="inegi_api"`
para que la UI lo distinga de un valor capturado a mano (ver migración 0019 y
adaptadores/http/gobierno_contexto.py, donde un PUT manual reescribe la fuente
a "manual")."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adaptadores.inegi import cliente_inegi
from app.models import ContextoInstitucional, Tenant


class SincronizacionInegiError(Exception):
    """Motivo legible de por qué no se pudo sincronizar -- el router HTTP la
    traduce a un 422/503 con este mismo mensaje, en español llano."""


def sincronizar_poblacion(db: Session, tenant: Tenant) -> ContextoInstitucional:
    """Consulta INEGI y actualiza (o crea) la fila de `contexto_institucional`
    del tenant. Lanza `SincronizacionInegiError` si el tenant no tiene
    `clave_geoestadistica` o si INEGI no está disponible/configurado -- quien
    llama decide el código HTTP, esta función solo decide el mensaje."""
    if not tenant.clave_geoestadistica:
        raise SincronizacionInegiError(
            "Este gobierno no tiene una clave geoestadística INEGI configurada -- "
            "no se puede sincronizar automáticamente todavía."
        )
    if not cliente_inegi.esta_disponible():
        raise SincronizacionInegiError(
            "La integración con INEGI no está configurada en este ambiente "
            "(falta INEGI_API_TOKEN)."
        )

    poblacion = cliente_inegi.obtener_poblacion_total(tenant.clave_geoestadistica)
    if poblacion is None:
        raise SincronizacionInegiError(
            "No se pudo obtener el dato de población desde INEGI en este momento. "
            "Intenta de nuevo más tarde, o captúralo manualmente."
        )

    fila = db.execute(
        select(ContextoInstitucional).where(ContextoInstitucional.tenant_id == tenant.id)
    ).scalar_one_or_none()
    if fila is None:
        fila = ContextoInstitucional(tenant_id=tenant.id)
        db.add(fila)

    fila.poblacion_total = poblacion
    fila.poblacion_total_fuente = "inegi_api"
    fila.actualizado_en = datetime.now(UTC)
    return fila


def resolver_tenant(db: Session, tenant_id: UUID) -> Tenant | None:
    return db.get(Tenant, tenant_id)

"""Bitácora persistida por trámite (migración 0012, pantalla "Historial") --
complementa a `app/core/audit_log.py` (que solo manda a stdout): esto queda
consultable desde el propio producto. `tipo` es texto libre en la base; las
constantes de abajo son el catálogo cerrado que este backend efectivamente
escribe, para no tener strings mágicos repetidos en cada router."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EventoHistorial

TIPO_DIAGNOSTICO_ENVIADO = "diagnostico_enviado"
TIPO_DIAGNOSTICO_CORREGIDO = "diagnostico_corregido"
TIPO_PLAN_GENERADO = "plan_generado"
TIPO_ACCION_ACTUALIZADA = "accion_actualizada"
TIPO_TRAMITE_ARCHIVADO = "tramite_archivado"
TIPO_TRAMITE_DESARCHIVADO = "tramite_desarchivado"


def registrar_evento(
    db: Session,
    *,
    tenant_id: UUID,
    tramite_id: UUID,
    tipo: str,
    descripcion: str,
    usuario_id: UUID | None = None,
    metadatos: dict | None = None,
) -> EventoHistorial:
    """No hace `commit()` -- se llama siempre desde dentro de la transacción del
    endpoint que dispara el evento, para que quede en el mismo commit (nunca un
    evento de historial persistido sin que la operación que describe también lo
    esté, ni viceversa)."""
    evento = EventoHistorial(
        tenant_id=tenant_id,
        tramite_id=tramite_id,
        usuario_id=usuario_id,
        tipo=tipo,
        descripcion=descripcion,
        metadatos=metadatos,
    )
    db.add(evento)
    db.flush()
    return evento


def listar_historial(db: Session, *, tenant_id: UUID, tramite_id: UUID) -> list[EventoHistorial]:
    """Más reciente primero -- misma convención que `docs/app-flow.md` describe
    para la línea de tiempo."""
    return list(
        db.execute(
            select(EventoHistorial)
            .where(EventoHistorial.tenant_id == tenant_id, EventoHistorial.tramite_id == tramite_id)
            .order_by(EventoHistorial.creado_en.desc())
        ).scalars()
    )

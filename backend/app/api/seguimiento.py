from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import AccionSeguimiento
from app.schemas.accion_seguimiento import AccionSeguimientoActualizarEstado, AccionSeguimientoOut

router = APIRouter(prefix="/api/seguimiento", tags=["seguimiento"])


@router.get("", response_model=list[AccionSeguimientoOut])
def listar_acciones(db: Annotated[Session, Depends(get_db)]) -> list[AccionSeguimiento]:
    """Todas las acciones de todos los trámites con plan generado (docs/app-flow.md,
    pantalla 5) — RLS ya filtra por tenant, no hace falta un WHERE adicional aquí."""
    return list(db.execute(select(AccionSeguimiento)).scalars())


@router.patch("/{accion_id}", response_model=AccionSeguimientoOut)
def actualizar_estado_semaforo(
    accion_id: UUID,
    payload: AccionSeguimientoActualizarEstado,
    db: Annotated[Session, Depends(get_db)],
) -> AccionSeguimiento:
    """Cambio de semáforo como acción simple en la misma tabla, sin pantalla aparte
    (docs/app-flow.md, mandato de 'sin metodologías pesadas')."""
    accion = db.get(AccionSeguimiento, accion_id)
    if accion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acción no encontrada")
    accion.estado_semaforo = payload.estado_semaforo
    db.commit()
    return accion

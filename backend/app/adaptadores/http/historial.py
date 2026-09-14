"""Historial (línea de tiempo) de un trámite -- ver app/aplicacion/historial.py
para el modelo de datos y el porqué complementa (no reemplaza) al log de stdout
de app/core/audit_log.py."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.adaptadores.http.deps import TokenData, get_current_token, get_db
from app.aplicacion.historial import listar_historial
from app.models import Tramite
from app.schemas.historial import EventoHistorialOut

router = APIRouter(prefix="/api/tramites", tags=["historial"])


@router.get("/{tramite_id}/historial", response_model=list[EventoHistorialOut])
def obtener_historial(
    tramite_id: UUID,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> list[EventoHistorialOut]:
    tramite = db.get(Tramite, tramite_id)
    if tramite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trámite no encontrado")

    eventos = listar_historial(db, tenant_id=token.tenant_id, tramite_id=tramite_id)
    return [EventoHistorialOut.model_validate(e) for e in eventos]

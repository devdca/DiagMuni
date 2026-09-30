"""Centro de notificaciones (campana de la barra superior) -- ver
app/aplicacion/notificaciones.py para el modelo y el porqué es tenant-wide."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.adaptadores.http.deps import TokenData, get_current_token, get_db
from app.aplicacion.notificaciones import (
    contar_no_leidas,
    generar_notificaciones_acciones_atrasadas,
    listar_notificaciones,
    marcar_leida,
    marcar_todas_leidas,
)
from app.db.rls import fijar_contexto_tenant
from app.schemas.notificacion import ListaNotificacionesOut, NotificacionOut

router = APIRouter(prefix="/api/notificaciones", tags=["notificaciones"])


@router.get("", response_model=ListaNotificacionesOut)
def listar(
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> ListaNotificacionesOut:
    """Antes de listar, genera (si hacen falta) las notificaciones de acciones
    recién atrasadas -- chequeo perezoso, sin cron (ver docstring de
    `generar_notificaciones_acciones_atrasadas`)."""
    generar_notificaciones_acciones_atrasadas(db, tenant_id=token.tenant_id)
    db.commit()
    fijar_contexto_tenant(db, token.tenant_id)

    notificaciones = listar_notificaciones(db, tenant_id=token.tenant_id)
    no_leidas = contar_no_leidas(db, tenant_id=token.tenant_id)
    return ListaNotificacionesOut(
        notificaciones=[NotificacionOut.model_validate(n) for n in notificaciones], no_leidas=no_leidas
    )


@router.post("/{notificacion_id}/leer", response_model=NotificacionOut)
def leer(
    notificacion_id: UUID,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificacionOut:
    notificacion = marcar_leida(db, tenant_id=token.tenant_id, notificacion_id=notificacion_id)
    if notificacion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada")
    db.commit()
    return NotificacionOut.model_validate(notificacion)


@router.post("/marcar-todas-leidas", status_code=status.HTTP_204_NO_CONTENT)
def leer_todas(
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    marcar_todas_leidas(db, tenant_id=token.tenant_id)
    db.commit()

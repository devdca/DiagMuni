from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import DiagnosticoTramite, PlanModernizacion
from app.schemas.plan import PlanOut

router = APIRouter(prefix="/api/tramites", tags=["planes"])


@router.get("/{tramite_id}/plan", response_model=PlanOut)
def obtener_plan_vigente(tramite_id: UUID, db: Annotated[Session, Depends(get_db)]) -> PlanModernizacion:
    """Última versión del plan — las anteriores no se borran pero no se muestran aquí
    (docs/app-flow.md: la vista siempre muestra la más reciente)."""
    diagnostico = db.execute(
        select(DiagnosticoTramite).where(DiagnosticoTramite.tramite_id == tramite_id)
    ).scalar_one_or_none()
    if diagnostico is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnóstico no iniciado")

    plan = db.execute(
        select(PlanModernizacion)
        .where(PlanModernizacion.diagnostico_tramite_id == diagnostico.id)
        .order_by(PlanModernizacion.version.desc())
        .limit(1)
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan aún no generado")
    return plan

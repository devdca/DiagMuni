from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TokenData, get_current_token, get_db
from app.jobs.plan_job import ejecutar_generacion_plan, verificar_watchdog_de_tramite
from app.models import DiagnosticoTramite, PlanModernizacion, Tramite
from app.schemas.plan import PlanOut

router = APIRouter(prefix="/api/tramites", tags=["planes"])


def _construir_plan_out(plan: PlanModernizacion, diagnostico: DiagnosticoTramite) -> PlanOut:
    """Arma el `PlanOut` explícito -- `PlanModernizacion` no tiene el índice de
    madurez (vive en `DiagnosticoTramite`, sin relationship ORM entre ambos, ver
    backend/app/models/plan_modernizacion.py)."""
    return PlanOut.model_validate(plan).model_copy(update={"indice_madurez": diagnostico.indice_madurez})


@router.get("/{tramite_id}/plan", response_model=PlanOut)
def obtener_plan_vigente(
    tramite_id: UUID,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> PlanOut:
    """Última versión del plan — las anteriores no se borran pero no se muestran aquí
    (docs/app-flow.md: la vista siempre muestra la más reciente)."""
    tramite = db.get(Tramite, tramite_id)
    if tramite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trámite no encontrado")

    job = verificar_watchdog_de_tramite(db, token.tenant_id, tramite)
    if job is not None:
        assert job.diagnostico_tramite_id is not None
        background_tasks.add_task(ejecutar_generacion_plan, job.id, token.tenant_id, job.diagnostico_tramite_id)

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
    return _construir_plan_out(plan, diagnostico)

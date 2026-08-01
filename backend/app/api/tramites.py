from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TokenData, get_current_token, get_db
from app.jobs.plan_job import ejecutar_generacion_plan, verificar_watchdog_de_tramite
from app.models import Tramite
from app.schemas.tramite import TramiteCreate, TramiteOut

router = APIRouter(prefix="/api/tramites", tags=["tramites"])


@router.get("", response_model=list[TramiteOut])
def listar_tramites(
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> list[Tramite]:
    tramites = list(db.execute(select(Tramite)).scalars())
    for tramite in tramites:
        job = verificar_watchdog_de_tramite(db, token.tenant_id, tramite)
        if job is not None:
            assert job.diagnostico_tramite_id is not None
            background_tasks.add_task(ejecutar_generacion_plan, job.id, token.tenant_id, job.diagnostico_tramite_id)
    return tramites


@router.post("", response_model=TramiteOut, status_code=status.HTTP_201_CREATED)
def crear_tramite(
    payload: TramiteCreate,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> Tramite:
    tramite = Tramite(tenant_id=token.tenant_id, nombre=payload.nombre, descripcion=payload.descripcion)
    db.add(tramite)
    db.commit()
    return tramite


@router.get("/{tramite_id}", response_model=TramiteOut)
def obtener_tramite(
    tramite_id: UUID,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> Tramite:
    """No hay una única ruta de frontend que consulte el estado del trámite
    (docs/app-flow.md no fija si es esta, el panel resumen o el polling directo
    del plan) -- por eso el chequeo perezoso de jobs obsoletos se repite en los
    tres endpoints de lectura, no solo acá (ver `app/jobs/plan_job.py`)."""
    tramite = db.get(Tramite, tramite_id)
    if tramite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trámite no encontrado")

    job = verificar_watchdog_de_tramite(db, token.tenant_id, tramite)
    if job is not None:
        assert job.diagnostico_tramite_id is not None
        background_tasks.add_task(ejecutar_generacion_plan, job.id, token.tenant_id, job.diagnostico_tramite_id)

    return tramite

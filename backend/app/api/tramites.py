from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TokenData, get_current_token, get_db
from app.engine.madurez import calcular_indice_global
from app.jobs.plan_job import ejecutar_generacion_plan, verificar_watchdog_de_tramite
from app.models import DiagnosticoTramite, Tramite
from app.schemas.tramite import PanelResumenOut, TramiteCreate, TramiteOut

router = APIRouter(prefix="/api/tramites", tags=["tramites"])


@router.get("", response_model=PanelResumenOut)
def listar_tramites(
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> PanelResumenOut:
    tramites = list(db.execute(select(Tramite)).scalars())
    for tramite in tramites:
        job = verificar_watchdog_de_tramite(db, token.tenant_id, tramite)
        if job is not None:
            assert job.diagnostico_tramite_id is not None
            background_tasks.add_task(ejecutar_generacion_plan, job.id, token.tenant_id, job.diagnostico_tramite_id)

    # Tramite y DiagnosticoTramite no tienen relación ORM declarada (docs de esta
    # tarea) -- se resuelve con una consulta explícita en vez de agregar una.
    ids_tramites = [tramite.id for tramite in tramites]
    diagnosticos_por_tramite = {
        diagnostico.tramite_id: diagnostico
        for diagnostico in db.execute(
            select(DiagnosticoTramite).where(DiagnosticoTramite.tramite_id.in_(ids_tramites))
        ).scalars()
    }

    tramites_out = []
    for tramite in tramites:
        diagnostico = diagnosticos_por_tramite.get(tramite.id)
        tramites_out.append(
            TramiteOut(
                id=tramite.id,
                nombre=tramite.nombre,
                descripcion=tramite.descripcion,
                estado=tramite.estado,
                created_at=tramite.created_at,
                updated_at=tramite.updated_at,
                indice_madurez=diagnostico.indice_madurez if diagnostico else None,
                completado_en=diagnostico.completado_en if diagnostico else None,
            )
        )

    fechas_completado = [t.completado_en for t in tramites_out if t.completado_en is not None]

    return PanelResumenOut(
        tramites=tramites_out,
        indice_global=calcular_indice_global([t.indice_madurez for t in tramites_out]),
        fecha_ultimo_diagnostico=max(fechas_completado) if fechas_completado else None,
    )


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

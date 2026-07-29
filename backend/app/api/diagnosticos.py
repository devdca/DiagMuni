from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TokenData, get_current_token, get_db
from app.engine.madurez import VERSION_MOTOR, calcular_indice_madurez
from app.jobs.plan_job import ejecutar_generacion_plan
from app.models import DiagnosticoTramite, Job, Tramite
from app.schemas.diagnostico import DiagnosticoEnviar, DiagnosticoGuardar, DiagnosticoOut

router = APIRouter(prefix="/api/tramites", tags=["diagnostico"])


def _obtener_o_crear_diagnostico(db: Session, tenant_id: UUID, tramite_id: UUID) -> DiagnosticoTramite:
    diagnostico = db.execute(
        select(DiagnosticoTramite).where(DiagnosticoTramite.tramite_id == tramite_id)
    ).scalar_one_or_none()
    if diagnostico is None:
        diagnostico = DiagnosticoTramite(tramite_id=tramite_id, tenant_id=tenant_id, respuestas={})
        db.add(diagnostico)
        db.flush()
    return diagnostico


@router.get("/{tramite_id}/diagnostico", response_model=DiagnosticoOut)
def obtener_diagnostico(tramite_id: UUID, db: Annotated[Session, Depends(get_db)]) -> DiagnosticoTramite:
    diagnostico = db.execute(
        select(DiagnosticoTramite).where(DiagnosticoTramite.tramite_id == tramite_id)
    ).scalar_one_or_none()
    if diagnostico is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnóstico no iniciado")
    return diagnostico


@router.put("/{tramite_id}/diagnostico", response_model=DiagnosticoOut)
def guardar_diagnostico(
    tramite_id: UUID,
    payload: DiagnosticoGuardar,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> DiagnosticoTramite:
    """'Guardar y continuar después' (docs/app-flow.md) — no calcula índice ni dispara plan."""
    tramite = db.get(Tramite, tramite_id)
    if tramite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trámite no encontrado")

    diagnostico = _obtener_o_crear_diagnostico(db, token.tenant_id, tramite_id)
    diagnostico.respuestas = payload.respuestas
    if tramite.estado == "sin_iniciar":
        tramite.estado = "en_progreso"
    db.commit()
    return diagnostico


@router.post("/{tramite_id}/diagnostico/enviar", response_model=DiagnosticoOut)
def enviar_diagnostico(
    tramite_id: UUID,
    payload: DiagnosticoEnviar,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> DiagnosticoTramite:
    """Envío completo: F2 (índice, síncrono y determinista) + dispara automáticamente
    el job de plan (docs/app-flow.md, máquina de estados: diagnosticado -> generando_plan,
    nunca requiere una acción manual adicional)."""
    tramite = db.get(Tramite, tramite_id)
    if tramite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trámite no encontrado")

    diagnostico = _obtener_o_crear_diagnostico(db, token.tenant_id, tramite_id)
    diagnostico.respuestas = payload.respuestas
    diagnostico.indice_madurez = calcular_indice_madurez(payload.respuestas)
    diagnostico.version_motor = VERSION_MOTOR
    diagnostico.completado_en = datetime.now(UTC)

    job = Job(tenant_id=token.tenant_id, tipo="generacion_plan", diagnostico_tramite_id=diagnostico.id)
    db.add(job)
    tramite.estado = "generando_plan"
    db.commit()

    background_tasks.add_task(ejecutar_generacion_plan, job.id, token.tenant_id, diagnostico.id)

    return diagnostico

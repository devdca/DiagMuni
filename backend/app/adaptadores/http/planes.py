from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adaptadores.http.deps import TokenData, get_current_token, get_db
from app.adaptadores.pdf.plan_pdf import generar_pdf_plan
from app.aplicacion.plan_job import _namespace_efectivo, ejecutar_generacion_plan, verificar_watchdog_de_tramite
from app.dominio.resumen_plan import (
    calcular_orden_sugerido,
    calcular_progreso_historico,
    calcular_resumen_inversion,
    calcular_resumen_personal,
)
from app.models import DiagnosticoTramite, PlanModernizacion, Tenant, Tramite
from app.schemas.plan import PlanOut, PlanVersionDetalleOut, VersionPlanResumen

router = APIRouter(prefix="/api/tramites", tags=["planes"])


def _diagnostico_de_tramite(tramite_id: UUID, db: Session) -> DiagnosticoTramite:
    diagnostico = db.execute(
        select(DiagnosticoTramite).where(DiagnosticoTramite.tramite_id == tramite_id)
    ).scalar_one_or_none()
    if diagnostico is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnóstico no iniciado")
    return diagnostico


def _resolver_plan_vigente(
    tramite_id: UUID, token: TokenData, db: Session, background_tasks: BackgroundTasks
) -> tuple[PlanModernizacion, DiagnosticoTramite]:
    """Resolución compartida por `obtener_plan_vigente` y `descargar_plan_pdf` --
    mismos 404 en el mismo orden, mismo watchdog de job obsoleto."""
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

    return plan, diagnostico


def _progreso_historico_de(db: Session, plan: PlanModernizacion) -> dict | None:
    """`None` si `plan.version == 1` (no hay versión anterior con la que comparar)
    -- si existe, calcula el diff determinista contra la versión inmediatamente
    anterior del mismo diagnóstico (app/engine/resumen_plan.py)."""
    if plan.version <= 1:
        return None

    plan_anterior = db.execute(
        select(PlanModernizacion).where(
            PlanModernizacion.diagnostico_tramite_id == plan.diagnostico_tramite_id,
            PlanModernizacion.version == plan.version - 1,
        )
    ).scalar_one_or_none()
    if plan_anterior is None:
        return None

    return calcular_progreso_historico(plan.contenido["brechas"], plan_anterior.contenido["brechas"])


def _contenido_con_faltantes(
    contenido: dict, db: Session, tenant_id: UUID, diagnostico: DiagnosticoTramite, tramite: Tramite, tenant: Tenant
) -> dict:
    """Planes generados antes de que `app/jobs/plan_job.py::_con_resumen` empezara a
    agregar `resumen_inversion`/`resumen_personal`/`orden_sugerido` no los tienen
    persistidos en `contenido` -- el frontend (`ContenidoPlan` en
    frontend/src/lib/planApi.ts) los da por presentes y truena si faltan. Se
    calculan acá al vuelo, mismo patrón de "no persistido, se arma en lectura" que
    ya usa `_progreso_historico_de` -- nunca se escribe de vuelta a la fila.

    `estimacion_recursos` NO se recalcula acá: requeriría una llamada a LLM en un
    GET (app/ia/estimacion_recursos.py) -- si falta, se completa con `None`, un
    valor ya válido para ese campo (mismo criterio que cuando no hay ruta de LLM
    disponible al generar)."""
    faltantes: dict = {}
    if any(clave not in contenido for clave in ("resumen_inversion", "resumen_personal", "orden_sugerido")):
        namespace_efectivo = _namespace_efectivo(db, tenant_id, diagnostico.respuestas, tramite.tipo)
        brechas = contenido["brechas"]
        if "resumen_inversion" not in contenido:
            faltantes["resumen_inversion"] = calcular_resumen_inversion(brechas, tenant.pais)
        if "resumen_personal" not in contenido:
            faltantes["resumen_personal"] = calcular_resumen_personal(brechas, namespace_efectivo, tenant.pais)
        if "orden_sugerido" not in contenido:
            faltantes["orden_sugerido"] = calcular_orden_sugerido(brechas)
    if "estimacion_recursos" not in contenido:
        faltantes["estimacion_recursos"] = None

    return {**contenido, **faltantes} if faltantes else contenido


def _construir_plan_out(
    plan: PlanModernizacion, diagnostico: DiagnosticoTramite, token: TokenData, db: Session
) -> PlanOut:
    """Arma el `PlanOut` explícito -- `PlanModernizacion` no tiene el índice de
    madurez (vive en `DiagnosticoTramite`, sin relationship ORM entre ambos, ver
    backend/app/models/plan_modernizacion.py)."""
    tramite = db.get(Tramite, diagnostico.tramite_id)
    tenant = db.get(Tenant, token.tenant_id)
    assert tramite is not None and tenant is not None  # ya resueltos por _resolver_plan_vigente

    contenido = _contenido_con_faltantes(plan.contenido, db, token.tenant_id, diagnostico, tramite, tenant)
    return PlanOut.model_validate(plan).model_copy(
        update={
            "contenido": contenido,
            "indice_madurez": diagnostico.indice_madurez,
            "progreso_historico": _progreso_historico_de(db, plan),
        }
    )


@router.get("/{tramite_id}/plan", response_model=PlanOut)
def obtener_plan_vigente(
    tramite_id: UUID,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> PlanOut:
    """Última versión del plan — las anteriores no se borran pero no se muestran aquí
    (docs/app-flow.md: la vista siempre muestra la más reciente)."""
    plan, diagnostico = _resolver_plan_vigente(tramite_id, token, db, background_tasks)
    return _construir_plan_out(plan, diagnostico, token, db)


@router.get("/{tramite_id}/plan/pdf")
def descargar_plan_pdf(
    tramite_id: UUID,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> Response:
    """PDF combinado (ejecutivo + técnico) del plan vigente -- mismos 404 que
    `obtener_plan_vigente`. `nombre_gobierno` se resuelve de `Tenant` en la base,
    nunca del JWT (`TokenData` deliberadamente no lo trae, ver app/api/deps.py)."""
    plan, diagnostico = _resolver_plan_vigente(tramite_id, token, db, background_tasks)
    plan_out = _construir_plan_out(plan, diagnostico, token, db)

    tenant = db.get(Tenant, token.tenant_id)
    nombre_gobierno = tenant.nombre if tenant is not None else ""

    pdf_bytes = generar_pdf_plan(plan_out, nombre_gobierno)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="plan-modernizacion.pdf"'},
    )


@router.get("/{tramite_id}/plan/versiones", response_model=list[VersionPlanResumen])
def listar_versiones_plan(
    tramite_id: UUID,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> list[VersionPlanResumen]:
    """Todas las versiones del plan de este trámite -- nunca se borran
    (docs/backend-schema.md). Alimenta el selector del comparador de versiones;
    más reciente primero."""
    tramite = db.get(Tramite, tramite_id)
    if tramite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trámite no encontrado")
    diagnostico = _diagnostico_de_tramite(tramite_id, db)

    planes = (
        db.execute(
            select(PlanModernizacion)
            .where(PlanModernizacion.diagnostico_tramite_id == diagnostico.id)
            .order_by(PlanModernizacion.version.desc())
        )
        .scalars()
        .all()
    )
    if not planes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan aún no generado")

    return [
        VersionPlanResumen(
            version=p.version,
            modo=p.modo,
            verificado=p.verificado,
            generado_en=p.generado_en,
            brechas_totales=len(p.contenido.get("brechas", [])),
        )
        for p in planes
    ]


@router.get("/{tramite_id}/plan/versiones/{version}", response_model=PlanVersionDetalleOut)
def obtener_version_plan(
    tramite_id: UUID,
    version: int,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> PlanVersionDetalleOut:
    """Detalle completo de UNA versión específica -- a diferencia de
    `obtener_plan_vigente`, no asume que es la última. Usado por el comparador de
    versiones para traer las dos versiones que el funcionario elija."""
    tramite = db.get(Tramite, tramite_id)
    if tramite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trámite no encontrado")
    diagnostico = _diagnostico_de_tramite(tramite_id, db)

    plan = db.execute(
        select(PlanModernizacion).where(
            PlanModernizacion.diagnostico_tramite_id == diagnostico.id,
            PlanModernizacion.version == version,
        )
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Esa versión del plan no existe")

    tenant = db.get(Tenant, token.tenant_id)
    assert tenant is not None
    contenido = _contenido_con_faltantes(plan.contenido, db, token.tenant_id, diagnostico, tramite, tenant)
    return PlanVersionDetalleOut(
        version=plan.version, modo=plan.modo, verificado=plan.verificado, generado_en=plan.generado_en,
        contenido=contenido,
    )

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adaptadores.http.deps import TokenData, get_current_token, get_db
from app.aplicacion.historial import TIPO_TRAMITE_ARCHIVADO, TIPO_TRAMITE_DESARCHIVADO, registrar_evento
from app.aplicacion.historial_indice_global import listar_historial_indice_global
from app.aplicacion.plan_job import ejecutar_generacion_plan, verificar_watchdog_de_tramite
from app.core.audit_log import registrar_tramite_archivado, registrar_tramite_desarchivado, registrar_tramite_eliminado
from app.db.rls import fijar_contexto_tenant
from app.dominio.madurez import calcular_indice_global
from app.dominio.tipos_tramite_loader import cargar_tipos_tramite
from app.models import DiagnosticoTramite, HistorialIndiceGlobal, Tramite
from app.schemas.tramite import (
    PanelResumenOut,
    PuntoIndiceGlobalOut,
    TipoTramiteOut,
    TramiteCreate,
    TramiteOut,
    VariableAdicionalOut,
)

router = APIRouter(prefix="/api/tramites", tags=["tramites"])


@router.get("/tipos", response_model=list[TipoTramiteOut])
def listar_tipos_tramite(token: Annotated[TokenData, Depends(get_current_token)]) -> list[TipoTramiteOut]:
    """Catálogo global (app/engine/tipos_tramite.yaml) -- no depende del tenant,
    solo requiere estar autenticado. Decide qué preguntas muestra Diagnostico.tsx
    para cada trámite."""
    return [
        TipoTramiteOut(
            nombre=t.nombre,
            etiqueta=t.etiqueta,
            variables_excluidas=sorted(t.variables_excluidas),
            variables_adicionales=[
                VariableAdicionalOut(variable=va.variable, pregunta=va.pregunta, ayuda=va.ayuda)
                for va in t.variables_adicionales
            ],
        )
        for t in cargar_tipos_tramite().values()
    ]


@router.get("", response_model=PanelResumenOut)
def listar_tramites(
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
    archivados: bool = False,
) -> PanelResumenOut:
    """`archivados=False` (default): solo activos, el índice global se calcula
    solo sobre esos -- un trámite archivado nunca debe inflarlo."""
    condicion = Tramite.archivado_en.is_not(None) if archivados else Tramite.archivado_en.is_(None)
    # order_by explícito -- sin él Postgres puede devolver filas en cualquier orden.
    tramites = list(
        db.execute(select(Tramite).where(condicion).order_by(Tramite.created_at.desc())).scalars()
    )
    for tramite in tramites:
        job = verificar_watchdog_de_tramite(db, token.tenant_id, tramite)
        if job is not None:
            assert job.diagnostico_tramite_id is not None
            background_tasks.add_task(ejecutar_generacion_plan, job.id, token.tenant_id, job.diagnostico_tramite_id)

    # Sin relación ORM declarada entre Tramite y DiagnosticoTramite -- consulta explícita.
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
                tipo=tramite.tipo,
                created_at=tramite.created_at,
                updated_at=tramite.updated_at,
                indice_madurez=diagnostico.indice_madurez if diagnostico else None,
                completado_en=diagnostico.completado_en if diagnostico else None,
                archivado_en=tramite.archivado_en,
            )
        )

    fechas_completado = [t.completado_en for t in tramites_out if t.completado_en is not None]

    return PanelResumenOut(
        tramites=tramites_out,
        indice_global=calcular_indice_global([t.indice_madurez for t in tramites_out]),
        fecha_ultimo_diagnostico=max(fechas_completado) if fechas_completado else None,
    )


@router.get("/indice-global/historial", response_model=list[PuntoIndiceGlobalOut])
def historial_indice_global(
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> list[HistorialIndiceGlobal]:
    """Tendencia real del índice global (migración 0015) -- un punto por cada
    envío/corrección de diagnóstico, nunca simulado. Ruta de dos segmentos
    ("/indice-global/historial") a propósito, para no chocar con
    GET /{tramite_id} de abajo -- ver también /tipos, mismo criterio.
    Devuelve el modelo ORM (no PuntoIndiceGlobalOut) -- `response_model` se
    encarga de la conversión, mismo patrón que `obtener_tramite` de abajo."""
    return listar_historial_indice_global(db, tenant_id=token.tenant_id)


@router.post("", response_model=TramiteOut, status_code=status.HTTP_201_CREATED)
def crear_tramite(
    payload: TramiteCreate,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> Tramite:
    tramite = Tramite(
        tenant_id=token.tenant_id, nombre=payload.nombre, descripcion=payload.descripcion, tipo=payload.tipo
    )
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


def _diagnostico_de(db: Session, tramite_id: UUID) -> DiagnosticoTramite | None:
    return db.execute(
        select(DiagnosticoTramite).where(DiagnosticoTramite.tramite_id == tramite_id)
    ).scalar_one_or_none()


@router.delete("/{tramite_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_tramite(
    tramite_id: UUID,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Borrado físico, permitido SOLO antes del primer envío de diagnóstico --
    guard basado en datos (`diagnostico.completado_en`), no en `estado` (que puede
    volver a `en_progreso` tras un plan ya generado, docs/app-flow.md "Casos
    especiales"). Con diagnóstico completado ya existen plan(es) versionados que
    `docs/backend-schema.md` exige nunca borrar, y una línea de auditoría real
    (`diagnostico_enviado`) que un borrado dejaría huérfana -- para ese caso, usar
    `POST /{tramite_id}/archivar` en su lugar."""
    tramite = db.get(Tramite, tramite_id)
    if tramite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trámite no encontrado")

    diagnostico = _diagnostico_de(db, tramite_id)
    if diagnostico is not None and diagnostico.completado_en is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No se puede eliminar un trámite con un diagnóstico ya enviado -- "
                "use 'Archivar' para ocultarlo sin perder su historial."
            ),
        )

    nombre = tramite.nombre
    if diagnostico is not None:
        db.delete(diagnostico)  # borrador sin enviar -- ver el guard de arriba
    db.delete(tramite)
    db.commit()

    registrar_tramite_eliminado(
        tenant_id=token.tenant_id, usuario_id=token.usuario_id, tramite_id=tramite_id, nombre=nombre
    )


@router.post("/{tramite_id}/archivar", response_model=TramiteOut)
def archivar_tramite(
    tramite_id: UUID,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> Tramite:
    """Reversible (ver `desarchivar_tramite`): no borra ninguna fila, solo saca al
    trámite del panel resumen (índice global, lista, fecha de último diagnóstico)
    y de `/api/seguimiento`. Sin restricción de estado -- a diferencia de
    `eliminar_tramite`, archivar un trámite recién catalogado (`sin_iniciar`) es
    válido, es solo una forma de ocultarlo del panel."""
    tramite = db.get(Tramite, tramite_id)
    if tramite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trámite no encontrado")
    if tramite.archivado_en is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El trámite ya está archivado.")

    tramite.archivado_en = datetime.now(UTC)
    registrar_evento(
        db,
        tenant_id=token.tenant_id,
        tramite_id=tramite_id,
        usuario_id=token.usuario_id,
        tipo=TIPO_TRAMITE_ARCHIVADO,
        descripcion=f'Trámite "{tramite.nombre}" archivado.',
    )
    db.commit()
    fijar_contexto_tenant(db, token.tenant_id)  # commit() resetea app.tenant_id

    registrar_tramite_archivado(
        tenant_id=token.tenant_id, usuario_id=token.usuario_id, tramite_id=tramite_id, nombre=tramite.nombre
    )
    return tramite


@router.post("/{tramite_id}/desarchivar", response_model=TramiteOut)
def desarchivar_tramite(
    tramite_id: UUID,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> Tramite:
    tramite = db.get(Tramite, tramite_id)
    if tramite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trámite no encontrado")
    if tramite.archivado_en is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El trámite no está archivado.")

    tramite.archivado_en = None
    registrar_evento(
        db,
        tenant_id=token.tenant_id,
        tramite_id=tramite_id,
        usuario_id=token.usuario_id,
        tipo=TIPO_TRAMITE_DESARCHIVADO,
        descripcion=f'Trámite "{tramite.nombre}" desarchivado.',
    )
    db.commit()
    fijar_contexto_tenant(db, token.tenant_id)

    registrar_tramite_desarchivado(
        tenant_id=token.tenant_id, usuario_id=token.usuario_id, tramite_id=tramite_id, nombre=tramite.nombre
    )
    return tramite

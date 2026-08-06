from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TokenData, get_current_token, get_db
from app.db.rls import fijar_contexto_tenant
from app.models import AccionSeguimiento, DiagnosticoTramite, PlanModernizacion, Tramite
from app.schemas.accion_seguimiento import AccionSeguimientoActualizar, AccionSeguimientoOut

router = APIRouter(prefix="/api/seguimiento", tags=["seguimiento"])


def _ids_planes_vigentes(versiones: list[tuple[UUID, UUID, int]]) -> set[UUID]:
    """De `(plan_id, diagnostico_tramite_id, version)` de todos los planes existentes,
    devuelve el `plan_id` de la versión más alta por `diagnostico_tramite_id` -- mismo
    criterio de "vigente" que `obtener_plan_vigente` (planes.py): última versión gana.

    Función pura para poder testearla sin sesión de DB real (mismo espíritu que
    `_construir_plan_out` en planes.py o `_esta_obsoleto` en plan_job.py)."""
    mejor_version_por_diagnostico: dict[UUID, tuple[int, UUID]] = {}
    for plan_id, diagnostico_tramite_id, version in versiones:
        mejor = mejor_version_por_diagnostico.get(diagnostico_tramite_id)
        if mejor is None or version > mejor[0]:
            mejor_version_por_diagnostico[diagnostico_tramite_id] = (version, plan_id)
    return {plan_id for _version, plan_id in mejor_version_por_diagnostico.values()}


def _construir_accion_out(accion: AccionSeguimiento, tramite_id: UUID, tramite_nombre: str) -> AccionSeguimientoOut:
    """Arma el `AccionSeguimientoOut` extendido -- `AccionSeguimiento` no tiene el
    trámite al que pertenece (sin relationship ORM entre esas tablas, ver
    backend/app/api/planes.py). Construcción explícita en vez de
    `model_validate(accion).model_copy(...)`: a diferencia de `indice_madurez` en
    `PlanOut`, acá no existe un valor por defecto razonable para `tramite_id`/
    `tramite_nombre` (toda acción pertenece a un trámite), así que `model_validate`
    fallaría por campos requeridos ausentes en el objeto ORM."""
    return AccionSeguimientoOut(
        id=accion.id,
        plan_modernizacion_id=accion.plan_modernizacion_id,
        descripcion=accion.descripcion,
        responsable=accion.responsable,
        fecha_objetivo=accion.fecha_objetivo,
        estado_semaforo=accion.estado_semaforo,
        actualizado_en=accion.actualizado_en,
        tramite_id=tramite_id,
        tramite_nombre=tramite_nombre,
    )


def _tramite_de_plan(db: Session, plan_modernizacion_id: UUID) -> tuple[UUID, str]:
    fila = db.execute(
        select(Tramite.id, Tramite.nombre)
        .select_from(PlanModernizacion)
        .join(DiagnosticoTramite, PlanModernizacion.diagnostico_tramite_id == DiagnosticoTramite.id)
        .join(Tramite, DiagnosticoTramite.tramite_id == Tramite.id)
        .where(PlanModernizacion.id == plan_modernizacion_id)
    ).one()
    return fila.id, fila.nombre


@router.get("", response_model=list[AccionSeguimientoOut])
def listar_acciones(db: Annotated[Session, Depends(get_db)]) -> list[AccionSeguimientoOut]:
    """Todas las acciones de la versión vigente de cada trámite con plan generado
    (docs/app-flow.md, pantalla 5) -- RLS ya filtra por tenant, no hace falta un
    WHERE adicional para eso; el filtro de acá es exclusivamente para no mezclar
    acciones de versiones de plan ya reemplazadas por una regeneración."""
    versiones = db.execute(
        select(PlanModernizacion.id, PlanModernizacion.diagnostico_tramite_id, PlanModernizacion.version)
    ).all()
    ids_vigentes = _ids_planes_vigentes([(fila.id, fila.diagnostico_tramite_id, fila.version) for fila in versiones])

    filas = db.execute(
        select(AccionSeguimiento, Tramite.id, Tramite.nombre)
        .join(PlanModernizacion, AccionSeguimiento.plan_modernizacion_id == PlanModernizacion.id)
        .join(DiagnosticoTramite, PlanModernizacion.diagnostico_tramite_id == DiagnosticoTramite.id)
        .join(Tramite, DiagnosticoTramite.tramite_id == Tramite.id)
        .where(AccionSeguimiento.plan_modernizacion_id.in_(ids_vigentes))
    ).all()
    return [_construir_accion_out(accion, tramite_id, tramite_nombre) for accion, tramite_id, tramite_nombre in filas]


@router.patch("/{accion_id}", response_model=AccionSeguimientoOut)
def actualizar_accion(
    accion_id: UUID,
    payload: AccionSeguimientoActualizar,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> AccionSeguimientoOut:
    """Edición inline de `responsable`, `fecha_objetivo` y/o `estado_semaforo` como
    acción simple en la misma tabla, sin pantalla aparte (docs/app-flow.md, mandato
    de 'sin metodologías pesadas'). `descripcion`, `plan_modernizacion_id` y
    `tenant_id` nunca son editables desde acá."""
    accion = db.get(AccionSeguimiento, accion_id)
    if accion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acción no encontrada")

    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(accion, campo, valor)
    db.commit()
    # commit() termina la transacción y con ella el app.tenant_id local (ver
    # app/db/rls.py) — hay que volver a fijarlo antes de la siguiente consulta.
    fijar_contexto_tenant(db, token.tenant_id)
    # `actualizado_en` usa `onupdate=func.now()` (calculado por Postgres); con
    # `expire_on_commit=False` (backend/app/db/session.py) el atributo Python no se
    # refresca solo tras el commit -- sin este refresh, la respuesta devolvería el
    # `actualizado_en` previo a esta edición.
    db.refresh(accion)

    tramite_id, tramite_nombre = _tramite_de_plan(db, accion.plan_modernizacion_id)
    return _construir_accion_out(accion, tramite_id, tramite_nombre)

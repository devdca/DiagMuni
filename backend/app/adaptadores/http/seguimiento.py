from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adaptadores.http.deps import TokenData, get_current_token, get_db
from app.aplicacion.historial import TIPO_ACCION_ACTUALIZADA, registrar_evento
from app.aplicacion.notas_seguimiento import crear_nota, listar_notas
from app.db.rls import fijar_contexto_tenant
from app.models import AccionSeguimiento, DiagnosticoTramite, PlanModernizacion, Tramite, Usuario
from app.schemas.accion_seguimiento import AccionSeguimientoActualizar, AccionSeguimientoOut
from app.schemas.nota_seguimiento import CrearNotaRequest, NotaSeguimientoOut

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
        .where(
            AccionSeguimiento.plan_modernizacion_id.in_(ids_vigentes),
            Tramite.archivado_en.is_(None),  # un trámite archivado sale también de seguimiento
        )
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

    tramite_id, tramite_nombre = _tramite_de_plan(db, accion.plan_modernizacion_id)

    cambios = payload.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(accion, campo, valor)

    if cambios:
        registrar_evento(
            db,
            tenant_id=token.tenant_id,
            tramite_id=tramite_id,
            usuario_id=token.usuario_id,
            tipo=TIPO_ACCION_ACTUALIZADA,
            descripcion=f'Acción "{accion.descripcion}" actualizada ({", ".join(sorted(cambios))}).',
        )

    db.commit()
    fijar_contexto_tenant(db, token.tenant_id)  # commit() resetea app.tenant_id
    db.refresh(accion)  # onupdate=func.now() no se refresca solo con expire_on_commit=False

    return _construir_accion_out(accion, tramite_id, tramite_nombre)


@router.get("/{accion_id}/notas", response_model=list[NotaSeguimientoOut])
def listar_notas_de_accion(
    accion_id: UUID,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> list[NotaSeguimientoOut]:
    accion = db.get(AccionSeguimiento, accion_id)
    if accion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acción no encontrada")

    notas = listar_notas(db, tenant_id=token.tenant_id, accion_seguimiento_id=accion_id)
    return [
        NotaSeguimientoOut(
            id=nota.id,
            accion_seguimiento_id=nota.accion_seguimiento_id,
            usuario_id=nota.usuario_id,
            usuario_nombre=nombre,
            texto=nota.texto,
            creado_en=nota.creado_en,
        )
        for nota, nombre in notas
    ]


@router.post("/{accion_id}/notas", response_model=NotaSeguimientoOut, status_code=status.HTTP_201_CREATED)
def agregar_nota_a_accion(
    accion_id: UUID,
    payload: CrearNotaRequest,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> NotaSeguimientoOut:
    accion = db.get(AccionSeguimiento, accion_id)
    if accion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acción no encontrada")

    nota = crear_nota(
        db, tenant_id=token.tenant_id, accion_seguimiento_id=accion_id, usuario_id=token.usuario_id, texto=payload.texto
    )
    db.commit()
    db.refresh(nota)

    usuario = db.get(Usuario, token.usuario_id)
    return NotaSeguimientoOut(
        id=nota.id,
        accion_seguimiento_id=nota.accion_seguimiento_id,
        usuario_id=nota.usuario_id,
        usuario_nombre=usuario.nombre if usuario is not None else "",
        texto=nota.texto,
        creado_en=nota.creado_en,
    )

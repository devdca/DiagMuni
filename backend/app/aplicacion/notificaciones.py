"""Centro de notificaciones (migración 0013, campana de la barra superior) --
tenant-wide, sin destinatario individual (ver docstring de la migración).
`tipo` es texto libre; las constantes de abajo son el catálogo cerrado que este
backend efectivamente escribe."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AccionSeguimiento, DiagnosticoTramite, Notificacion, PlanModernizacion, Tramite

TIPO_ACCION_ATRASADA = "accion_atrasada"
TIPO_PLAN_GENERADO = "plan_generado"
TIPO_PLAN_DEGRADADO = "plan_degradado"


def crear_notificacion(
    db: Session,
    *,
    tenant_id: UUID,
    tipo: str,
    titulo: str,
    mensaje: str,
    tramite_id: UUID | None = None,
    accion_seguimiento_id: UUID | None = None,
) -> Notificacion:
    """No hace `commit()` -- mismo criterio que `historial.registrar_evento`: se
    llama dentro de la transacción del endpoint (o del job) que dispara la
    notificación."""
    notificacion = Notificacion(
        tenant_id=tenant_id,
        tramite_id=tramite_id,
        accion_seguimiento_id=accion_seguimiento_id,
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
    )
    db.add(notificacion)
    db.flush()
    return notificacion


def listar_notificaciones(db: Session, *, tenant_id: UUID, limite: int = 30) -> list[Notificacion]:
    return list(
        db.execute(
            select(Notificacion)
            .where(Notificacion.tenant_id == tenant_id)
            .order_by(Notificacion.creado_en.desc())
            .limit(limite)
        ).scalars()
    )


def contar_no_leidas(db: Session, *, tenant_id: UUID) -> int:
    return db.execute(
        select(func.count())
        .select_from(Notificacion)
        .where(Notificacion.tenant_id == tenant_id, Notificacion.leida.is_(False))
    ).scalar_one()


def marcar_leida(db: Session, *, tenant_id: UUID, notificacion_id: UUID) -> Notificacion | None:
    notificacion = db.execute(
        select(Notificacion).where(Notificacion.tenant_id == tenant_id, Notificacion.id == notificacion_id)
    ).scalar_one_or_none()
    if notificacion is None:
        return None
    notificacion.leida = True
    db.flush()
    return notificacion


def marcar_todas_leidas(db: Session, *, tenant_id: UUID) -> None:
    notificaciones = db.execute(
        select(Notificacion).where(Notificacion.tenant_id == tenant_id, Notificacion.leida.is_(False))
    ).scalars()
    for notificacion in notificaciones:
        notificacion.leida = True
    db.flush()


def generar_notificaciones_acciones_atrasadas(db: Session, *, tenant_id: UUID) -> None:
    """Chequeo perezoso disparado al listar notificaciones -- sin cron ni scheduler
    (mismo criterio sin infraestructura nueva que `revisar_job_obsoleto`,
    app/aplicacion/plan_job.py). "Atrasada" se deriva de `fecha_objetivo < hoy` y
    `estado_semaforo != completado` -- NUNCA escribe de vuelta `estado_semaforo`
    (ese campo lo sigue decidiendo el funcionario a mano, F6); esto solo decide si
    hace falta avisar. Deduplicado por `accion_seguimiento_id`: una vez creada la
    notificación de una acción, no se repite aunque siga atrasada en la próxima
    revisión (evita spam) -- no hace `commit()`, igual que el resto de este módulo."""
    hoy = date.today()
    filas = db.execute(
        select(AccionSeguimiento, Tramite.id, Tramite.nombre)
        .join(PlanModernizacion, AccionSeguimiento.plan_modernizacion_id == PlanModernizacion.id)
        .join(DiagnosticoTramite, PlanModernizacion.diagnostico_tramite_id == DiagnosticoTramite.id)
        .join(Tramite, DiagnosticoTramite.tramite_id == Tramite.id)
        .where(
            AccionSeguimiento.fecha_objetivo < hoy,
            AccionSeguimiento.estado_semaforo != "completado",
            Tramite.archivado_en.is_(None),
        )
    ).all()

    for accion, tramite_id, tramite_nombre in filas:
        ya_existe = db.execute(
            select(Notificacion.id).where(
                Notificacion.tenant_id == tenant_id,
                Notificacion.accion_seguimiento_id == accion.id,
                Notificacion.tipo == TIPO_ACCION_ATRASADA,
            )
        ).scalar_one_or_none()
        if ya_existe is not None:
            continue

        dias = (hoy - accion.fecha_objetivo).days
        crear_notificacion(
            db,
            tenant_id=tenant_id,
            tipo=TIPO_ACCION_ATRASADA,
            tramite_id=tramite_id,
            accion_seguimiento_id=accion.id,
            titulo="Acción atrasada",
            mensaje=f'"{accion.descripcion}" venció hace {dias} día(s) -- {tramite_nombre}.',
        )

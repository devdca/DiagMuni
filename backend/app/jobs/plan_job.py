"""Job asíncrono de generación de plan (docs/TRD.md, "Job asíncrono — ciclo de vida").

`_generar_contenido_y_modo` nunca persiste `verificado=False` (docs/backend-schema.md:
un plan no verificado nunca se muestra). Sin ruta `calidad` disponible, genera
directo en modo degradado; si el verificador aprueba el contenido LLM, se persiste
en modo `llm`; si lo rechaza o el verificador falla, se descarta y se persiste el
contenido determinista. Los tres caminos terminan en `verificado=True` -- el
degradado es correcto por construcción, el LLM ya pasó auditoría.

Es una función pura (sin sesión de DB) para poder testearla sin Postgres real; el
resto del job sigue siendo el único responsable de la sesión y de la tabla `job`.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.engine.plantillas import generar_contenido_degradado
from app.ia.config import esta_disponible
from app.ia.generador_plan import generar_contenido_llm
from app.ia.verificador import verificar_contenido
from app.models import AccionSeguimiento, DiagnosticoTramite, Job, PlanModernizacion, Tenant, Tramite

# Ruta que generador_plan.py usa para redactar -- si no está disponible, no hay
# nada que generar vía LLM.
_RUTA_GENERACION = "calidad"

# docs/app-flow.md, máquina de estados: "si falla dos veces -> plan_listo en modo
# degradado". Un mismo contador (`Job.intentos`) cuenta tanto fallos por excepción
# como detecciones de job obsoleto -- ver `revisar_job_obsoleto`.
LIMITE_INTENTOS = 2

# Sin blueprint que fije un plazo -- 90 días (un trimestre) como horizonte por
# defecto, editable por el funcionario desde el panel de seguimiento (F6).
_DIAS_PLAZO_ACCION_SEGUIMIENTO = 90
_RESPONSABLE_SIN_ASIGNAR = "Por asignar"


def _crear_acciones_seguimiento(db: Session, plan: PlanModernizacion, tenant_id: UUID) -> None:
    """Una `AccionSeguimiento` por brecha del plan recién persistido (F6, docs/
    app-flow.md paso 5) -- `descripcion` toma `paso_administrativo`, el paso corto y
    accionable de cada brecha (presente en ambos modos, `degradado` y `llm`, ver
    app/engine/plantillas.py y app/ia/generador_plan.py), no la `narrativa` completa
    que ya se muestra en el plan. `fecha_objetivo` se calcula en Python -- no se
    puede leer `plan.generado_en` sin refrescar la fila porque es `server_default`.
    Requiere que `plan.id` ya exista (llamar después de `db.flush()`)."""
    fecha_objetivo = datetime.now(UTC).date() + timedelta(days=_DIAS_PLAZO_ACCION_SEGUIMIENTO)
    for brecha in plan.contenido["brechas"]:
        db.add(
            AccionSeguimiento(
                plan_modernizacion_id=plan.id,
                tenant_id=tenant_id,
                descripcion=brecha["paso_administrativo"],
                responsable=_RESPONSABLE_SIN_ASIGNAR,
                fecha_objetivo=fecha_objetivo,
            )
        )


def _generar_contenido_y_modo(respuestas: dict, pais: str) -> tuple[str, dict, bool]:
    """Devuelve `(modo, contenido, verificado)` -- `verificado` siempre `True`."""
    if not esta_disponible(_RUTA_GENERACION):
        return "degradado", generar_contenido_degradado(respuestas, pais), True

    contenido_llm = generar_contenido_llm(respuestas, pais)
    contenido_determinista = generar_contenido_degradado(respuestas, pais)

    if verificar_contenido(contenido_llm, contenido_determinista):
        return "llm", contenido_llm, True

    # verificar_contenido ya es fail-closed (rechazo, fallo o no disponible = no
    # aprobado); en cualquier caso se descarta el LLM y se persiste el determinista.
    return "degradado", contenido_determinista, True


def _persistir_plan_degradado(db: Session, tenant_id: UUID, diagnostico_tramite_id: UUID) -> bool:
    """Genera y persiste el plan en modo degradado y cierra el trámite -- mismo
    patrón de versionado y transición de estado que el camino feliz de
    `ejecutar_generacion_plan`, sin intentar la ruta LLM. Devuelve `False` sin
    persistir nada si el diagnóstico o el tenant ya no existen. No hace commit --
    lo hace quien la invoca."""
    diagnostico = db.get(DiagnosticoTramite, diagnostico_tramite_id)
    tenant = db.get(Tenant, tenant_id)
    if diagnostico is None or tenant is None:
        return False

    version_previa = db.execute(
        select(PlanModernizacion.version)
        .where(PlanModernizacion.diagnostico_tramite_id == diagnostico_tramite_id)
        .order_by(PlanModernizacion.version.desc())
        .limit(1)
    ).scalar_one_or_none()

    plan = PlanModernizacion(
        diagnostico_tramite_id=diagnostico_tramite_id,
        tenant_id=tenant_id,
        version=(version_previa or 0) + 1,
        modo="degradado",
        contenido=generar_contenido_degradado(diagnostico.respuestas, tenant.pais),
        verificado=True,
    )
    db.add(plan)
    db.flush()
    _crear_acciones_seguimiento(db, plan, tenant_id)

    tramite = db.get(Tramite, diagnostico.tramite_id)
    if tramite is not None:
        tramite.estado = "plan_listo"
    return True


def ejecutar_generacion_plan(job_id: UUID, tenant_id: UUID, diagnostico_tramite_id: UUID) -> None:
    db = abrir_sesion_tenant(tenant_id)
    try:
        job = db.get(Job, job_id)
        if job is None:
            return

        job.estado = "running"
        db.commit()
        # commit() termina la transacción y con ella el app.tenant_id local (ver
        # app/db/rls.py) — hay que volver a fijarlo antes de la siguiente consulta.
        fijar_contexto_tenant(db, tenant_id)

        diagnostico = db.get(DiagnosticoTramite, diagnostico_tramite_id)
        tenant = db.get(Tenant, tenant_id)
        if diagnostico is None or tenant is None:
            job.estado = "failed"
            job.intentos += 1
            db.commit()
            return

        modo, contenido, verificado = _generar_contenido_y_modo(diagnostico.respuestas, tenant.pais)

        version_previa = db.execute(
            select(PlanModernizacion.version)
            .where(PlanModernizacion.diagnostico_tramite_id == diagnostico_tramite_id)
            .order_by(PlanModernizacion.version.desc())
            .limit(1)
        ).scalar_one_or_none()

        plan = PlanModernizacion(
            diagnostico_tramite_id=diagnostico_tramite_id,
            tenant_id=tenant_id,
            version=(version_previa or 0) + 1,
            modo=modo,
            contenido=contenido,
            verificado=verificado,
        )
        db.add(plan)
        db.flush()
        _crear_acciones_seguimiento(db, plan, tenant_id)

        tramite = db.get(Tramite, diagnostico.tramite_id)
        if tramite is not None:
            tramite.estado = "plan_listo"

        job.estado = "done"
        db.commit()
    except Exception:
        db.rollback()
        # rollback() también termina la transacción — mismo motivo que tras el commit de arriba.
        fijar_contexto_tenant(db, tenant_id)
        job = db.get(Job, job_id)
        if job is not None:
            job.intentos += 1
            if job.intentos >= LIMITE_INTENTOS:
                # docs/app-flow.md: "si falla dos veces -> plan_listo en modo degradado".
                # El trámite no puede quedar colgado en generando_plan esperando un
                # tercer intento que nunca llega.
                if _persistir_plan_degradado(db, tenant_id, diagnostico_tramite_id):
                    job.estado = "done"
                else:
                    job.estado = "failed"
            else:
                job.estado = "failed"
            db.commit()
        raise
    finally:
        db.close()


def _esta_obsoleto(actualizado_en: datetime, umbral_minutos: int, ahora: datetime | None = None) -> bool:
    """True si `actualizado_en` es más viejo que `umbral_minutos` -- proceso
    reiniciado a medio job (docs/TRD.md, "Job asíncrono — ciclo de vida")."""
    ahora = ahora or datetime.now(UTC)
    if actualizado_en.tzinfo is None:
        actualizado_en = actualizado_en.replace(tzinfo=UTC)
    return ahora - actualizado_en > timedelta(minutes=umbral_minutos)


def obtener_job_vigente(db: Session, diagnostico_tramite_id: UUID) -> Job | None:
    """Job de generación de plan más reciente de un diagnóstico -- a lo sumo uno en
    curso por diagnóstico (ver `enviar_diagnostico`)."""
    return db.execute(
        select(Job)
        .where(Job.diagnostico_tramite_id == diagnostico_tramite_id, Job.tipo == "generacion_plan")
        .order_by(Job.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def revisar_job_obsoleto(db: Session, tenant_id: UUID, job: Job) -> bool:
    """Chequeo perezoso disparado al leer un trámite en `generando_plan` (sin
    scheduler ni cron -- ver `docs/TRD.md`). Cubre dos orígenes de job sin
    terminar:

    - `failed`: ya pasó por el bloque `except` de `ejecutar_generacion_plan`, que
      ya incrementó `intentos`. Normalmente hay margen y solo hace falta
      redisparar sin volver a incrementar -- pero si `intentos` ya alcanzó
      `LIMITE_INTENTOS` (caso de borde: el `except` forzó el degradado y
      `_persistir_plan_degradado` no pudo persistir porque el diagnóstico o el
      tenant ya no existen), acá se reintenta el degradado en vez de
      redisparar, igual que en la rama `running` de abajo -- así se evita un
      ciclo `failed -> pending -> failed` indefinido.
    - `running` sin actualizar hace más de `settings.job_umbral_obsoleto_minutos`:
      el proceso reinició a medio job y nunca llegó al bloque `except`, así que
      acá sí hay que incrementar (representa un intento real concluido por crash)
      antes de decidir si queda margen -- mismo orden que el bloque `except`.

    Devuelve `True` si el llamador debe encolar `ejecutar_generacion_plan` vía
    `BackgroundTasks` (no se ejecuta acá para no bloquear la respuesta HTTP con
    una llamada LLM síncrona). Devuelve `False` si ya se agotó `LIMITE_INTENTOS`
    (el degradado ya se forzó de forma síncrona acá mismo) o si el job no está
    en un estado que requiera acción.
    """
    if job.diagnostico_tramite_id is None:
        return False

    if job.estado == "failed":
        if job.intentos >= LIMITE_INTENTOS:
            # Caso de borde: el `except` (o la rama `running` de abajo) alcanzó
            # LIMITE_INTENTOS pero `_persistir_plan_degradado` no pudo persistir
            # (diagnóstico o tenant ya no existen) y dejó el job en `failed` en
            # vez de `done`. Sin este chequeo, acá se reintentaría sin límite en
            # un ciclo failed -> pending -> failed indefinido. Mismo patrón que
            # la rama `running`: se reintenta el degradado, no se redispara
            # `ejecutar_generacion_plan`.
            if _persistir_plan_degradado(db, tenant_id, job.diagnostico_tramite_id):
                job.estado = "done"
            else:
                job.estado = "failed"
            db.commit()
            # commit() termina la transacción y con ella el app.tenant_id local (ver
            # app/db/rls.py) — hay que volver a fijarlo antes de la siguiente consulta.
            fijar_contexto_tenant(db, tenant_id)
            return False

        job.estado = "pending"
        db.commit()
        # mismo motivo que el commit anterior en esta función: hay que refijar el
        # contexto de tenant tras cada commit (ver comentario de arriba).
        fijar_contexto_tenant(db, tenant_id)
        return True

    if job.estado == "running" and _esta_obsoleto(job.updated_at, settings.job_umbral_obsoleto_minutos):
        job.intentos += 1
        if job.intentos >= LIMITE_INTENTOS:
            if _persistir_plan_degradado(db, tenant_id, job.diagnostico_tramite_id):
                job.estado = "done"
            else:
                job.estado = "failed"
            db.commit()
            # mismo motivo que el primer commit de esta función: hay que refijar el
            # contexto de tenant tras cada commit.
            fijar_contexto_tenant(db, tenant_id)
            return False

        job.estado = "pending"
        db.commit()
        # mismo motivo que el primer commit de esta función: hay que refijar el
        # contexto de tenant tras cada commit.
        fijar_contexto_tenant(db, tenant_id)
        return True

    return False


def verificar_watchdog_de_tramite(db: Session, tenant_id: UUID, tramite: Tramite) -> Job | None:
    """Si el trámite está en `generando_plan`, revisa su job vigente y lo marca
    para reintento si corresponde. Devuelve el job a redisparar vía
    `BackgroundTasks`, o `None` si no hay nada que redisparar."""
    if tramite.estado != "generando_plan":
        return None

    diagnostico = db.execute(
        select(DiagnosticoTramite).where(DiagnosticoTramite.tramite_id == tramite.id)
    ).scalar_one_or_none()
    if diagnostico is None:
        return None

    job = obtener_job_vigente(db, diagnostico.id)
    if job is None or not revisar_job_obsoleto(db, tenant_id, job):
        return None
    return job

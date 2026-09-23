"""Job asíncrono de generación de plan (docs/TRD.md, "Job asíncrono — ciclo de vida").

Un plan siempre queda `verificado=True`: si no hay LLM disponible o el verificador
rechaza el contenido, se persiste el degradado (correcto por construcción); si el
verificador aprueba, se persiste el modo `llm`.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adaptadores.llm.config import OverrideLlmTenant, esta_disponible, obtener_rutas_generacion
from app.adaptadores.llm.contexto_gobierno import formatear_contexto_gobierno
from app.adaptadores.llm.estimacion_recursos import generar_estimacion_recursos
from app.adaptadores.llm.generador_plan import generar_contenido_llm
from app.adaptadores.llm.sugerencia_libre import generar_sugerencia_libre
from app.adaptadores.llm.verificador import verificar_contenido
from app.aplicacion.historial import TIPO_PLAN_GENERADO as _TIPO_HISTORIAL_PLAN_GENERADO
from app.aplicacion.historial import registrar_evento
from app.aplicacion.notificaciones import TIPO_PLAN_DEGRADADO, TIPO_PLAN_GENERADO, crear_notificacion
from app.aplicacion.preferencia_modelo_ia import resolver_override
from app.core.config import settings
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.dominio.plantillas import generar_contenido_degradado
from app.dominio.resumen_plan import (
    calcular_factibilidad,
    calcular_orden_sugerido,
    calcular_resumen_inversion,
    calcular_resumen_personal,
)
from app.dominio.tipos_tramite_loader import completar_respuestas_no_aplicables, evaluar_brechas_adicionales
from app.models import (
    AccionSeguimiento,
    ContextoInstitucional,
    DiagnosticoTramite,
    Job,
    PlanModernizacion,
    Tenant,
    Tramite,
)

# Si falla 2 veces (excepción o job obsoleto), cae a modo degradado.
LIMITE_INTENTOS = 2

_DIAS_PLAZO_ACCION_SEGUIMIENTO = 90  # horizonte por defecto, editable en F6
_RESPONSABLE_SIN_ASIGNAR = "Por asignar"


def _crear_acciones_seguimiento(db: Session, plan: PlanModernizacion, tenant_id: UUID) -> None:
    """Una `AccionSeguimiento` por brecha del plan (F6). Requiere `plan.id` ya
    asignado (llamar después de `db.flush()`)."""
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


def _namespace_efectivo(db: Session, tenant_id: UUID, respuestas: dict, tipo_tramite: str) -> dict:
    """Fusión `{**contexto_institucional_del_tenant, **respuestas_del_tramite}`
    para evaluar brechas transversales junto a las del trámite. Completa al final
    las variables que `tipo_tramite` no pregunta, para que no cuenten como brecha."""
    contexto = db.execute(
        select(ContextoInstitucional).where(ContextoInstitucional.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if contexto is None:
        namespace = dict(respuestas)
    else:
        # Se deriva de las columnas reales del modelo (no una lista a mano) --
        # bug de QA previo: una lista escrita a mano se quedó atrás de una
        # migración y perdía campos reales en silencio.
        namespace_contexto = {
            columna.key: getattr(contexto, columna.key)
            for columna in ContextoInstitucional.__table__.columns
            if columna.key not in {"id", "tenant_id", "actualizado_en", "created_at"}
        }
        namespace = {**namespace_contexto, **respuestas}

    return completar_respuestas_no_aplicables(tipo_tramite, namespace)


def _con_brechas_adicionales(contenido: dict, tipo_tramite: str, respuestas: dict) -> dict:
    """Agrega las brechas propias del tipo de trámite -- siempre determinista,
    nunca pasa por el LLM. No-op segura para `"generico"`."""
    brechas_adicionales = evaluar_brechas_adicionales(tipo_tramite, respuestas)
    if not brechas_adicionales:
        return contenido
    brechas = [*contenido["brechas"], *brechas_adicionales]
    resumen = f"Se detectaron {len(brechas)} brecha(s) de modernización. Ver detalle de cada una a continuación."
    return {**contenido, "brechas": brechas, "resumen_narrativo": resumen}


def _con_sugerencia_libre(
    contenido: dict, descripcion: str, respuestas: dict, pais: str, *, override: OverrideLlmTenant | None = None
) -> dict:
    """Sugerencia libre generada de la descripción del trámite -- complementa las
    brechas, nunca pasa por el verificador F9. `None` sin descripción o sin LLM."""
    return {
        **contenido,
        "sugerencia_libre": generar_sugerencia_libre(descripcion, respuestas, pais, override=override),
    }


def _con_estimacion_recursos(
    contenido: dict, respuestas: dict, pais: str, *, override: OverrideLlmTenant | None = None
) -> dict:
    """Estimación aproximada de personal/presupuesto -- mismo criterio que
    `_con_sugerencia_libre`: texto libre de IA, sin verificador F9."""
    return {
        **contenido,
        "estimacion_recursos": generar_estimacion_recursos(
            contenido["brechas"], respuestas, pais, override=override
        ),
    }


def _con_resumen(contenido: dict, respuestas: dict, pais: str) -> dict:
    """Síntesis determinista de presupuesto/personal/orden sugerido, calculada
    sobre `contenido["brechas"]` ya completo (con `factibilidad` ya agregada)."""
    brechas = [{**brecha, "factibilidad": calcular_factibilidad(brecha, respuestas)} for brecha in contenido["brechas"]]
    return {
        **contenido,
        "brechas": brechas,
        "resumen_inversion": calcular_resumen_inversion(brechas, pais),
        "resumen_personal": calcular_resumen_personal(brechas, respuestas, pais),
        "orden_sugerido": calcular_orden_sugerido(brechas),
    }


def _generar_contenido_y_modo(
    respuestas: dict,
    pais: str,
    tipo_tramite: str = "generico",
    descripcion: str = "",
    nivel_gobierno: str = "municipal",
    *,
    override: OverrideLlmTenant | None = None,
) -> tuple[str, dict, bool]:
    """Devuelve `(modo, contenido, verificado)` -- `verificado` siempre `True`.
    `override` (BYOK): credencial del tenant, gana sobre la config global."""
    rutas_generacion = obtener_rutas_generacion(override=override)
    if not any(esta_disponible(nombre, override=override) for nombre in rutas_generacion):
        contenido = generar_contenido_degradado(respuestas, pais, nivel_gobierno, tipo_tramite)
        contenido = _con_brechas_adicionales(contenido, tipo_tramite, respuestas)
        contenido = _con_resumen(contenido, respuestas, pais)
        contenido = _con_sugerencia_libre(contenido, descripcion, respuestas, pais, override=override)
        return "degradado", _con_estimacion_recursos(contenido, respuestas, pais, override=override), True

    contenido_llm = generar_contenido_llm(respuestas, pais, nivel_gobierno, tipo_tramite, override=override)
    contenido_determinista = generar_contenido_degradado(respuestas, pais, nivel_gobierno, tipo_tramite)
    contexto_gobierno = formatear_contexto_gobierno(respuestas, pais)

    if verificar_contenido(contenido_llm, contenido_determinista, contexto_gobierno, override=override):
        contenido = _con_brechas_adicionales(contenido_llm, tipo_tramite, respuestas)
        contenido = _con_resumen(contenido, respuestas, pais)
        contenido = _con_sugerencia_libre(contenido, descripcion, respuestas, pais, override=override)
        return "llm", _con_estimacion_recursos(contenido, respuestas, pais, override=override), True

    # Rechazo, fallo o no disponible: se descarta el LLM y se persiste el determinista.
    contenido = _con_brechas_adicionales(contenido_determinista, tipo_tramite, respuestas)
    contenido = _con_resumen(contenido, respuestas, pais)
    contenido = _con_sugerencia_libre(contenido, descripcion, respuestas, pais, override=override)
    return "degradado", _con_estimacion_recursos(contenido, respuestas, pais, override=override), True


def _registrar_plan_generado(db: Session, *, tenant_id: UUID, tramite: Tramite, plan: PlanModernizacion) -> None:
    """Historial + notificación del evento "se generó un plan" -- punto único
    compartido por los dos caminos que pueden crear un `PlanModernizacion`."""
    registrar_evento(
        db,
        tenant_id=tenant_id,
        tramite_id=tramite.id,
        tipo=_TIPO_HISTORIAL_PLAN_GENERADO,
        descripcion=f"Plan de modernización generado -- versión {plan.version}, modo {plan.modo}.",
        metadatos={"version": plan.version, "modo": plan.modo},
    )
    if plan.modo == "degradado":
        crear_notificacion(
            db,
            tenant_id=tenant_id,
            tramite_id=tramite.id,
            tipo=TIPO_PLAN_DEGRADADO,
            titulo="Plan generado en modo degradado",
            mensaje=(
                f'"{tramite.nombre}" se generó con plantilla determinista (versión {plan.version}) -- '
                "la API de IA no respondió o no estaba disponible."
            ),
        )
    else:
        crear_notificacion(
            db,
            tenant_id=tenant_id,
            tramite_id=tramite.id,
            tipo=TIPO_PLAN_GENERADO,
            titulo="Plan generado",
            mensaje=f'Nueva versión ({plan.version}) del plan de "{tramite.nombre}" ya está lista.',
        )


def _persistir_plan_degradado(db: Session, tenant_id: UUID, diagnostico_tramite_id: UUID) -> bool:
    """Genera y persiste el plan en modo degradado (sin intentar LLM) y cierra el
    trámite. `False` sin persistir si el diagnóstico o el tenant ya no existen.
    No hace commit -- lo hace quien la invoca."""
    diagnostico = db.get(DiagnosticoTramite, diagnostico_tramite_id)
    tenant = db.get(Tenant, tenant_id)
    if diagnostico is None or tenant is None:
        return False

    tramite = db.get(Tramite, diagnostico.tramite_id)
    if tramite is None:
        return False

    version_previa = db.execute(
        select(PlanModernizacion.version)
        .where(PlanModernizacion.diagnostico_tramite_id == diagnostico_tramite_id)
        .order_by(PlanModernizacion.version.desc())
        .limit(1)
    ).scalar_one_or_none()

    # Las brechas siempre son degradado a propósito; sugerencia/estimación sí
    # usan la credencial propia del tenant si existe (BYOK).
    override = resolver_override(tenant)
    namespace_efectivo = _namespace_efectivo(db, tenant_id, diagnostico.respuestas, tramite.tipo)
    contenido = _con_brechas_adicionales(
        generar_contenido_degradado(namespace_efectivo, tenant.pais, tenant.nivel_gobierno, tramite.tipo),
        tramite.tipo,
        namespace_efectivo,
    )
    contenido = _con_resumen(contenido, namespace_efectivo, tenant.pais)
    contenido = _con_sugerencia_libre(
        contenido, tramite.descripcion, namespace_efectivo, tenant.pais, override=override
    )
    contenido = _con_estimacion_recursos(contenido, namespace_efectivo, tenant.pais, override=override)
    plan = PlanModernizacion(
        diagnostico_tramite_id=diagnostico_tramite_id,
        tenant_id=tenant_id,
        version=(version_previa or 0) + 1,
        modo="degradado",
        contenido=contenido,
        verificado=True,
    )
    db.add(plan)
    db.flush()
    _crear_acciones_seguimiento(db, plan, tenant_id)
    _registrar_plan_generado(db, tenant_id=tenant_id, tramite=tramite, plan=plan)

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
        fijar_contexto_tenant(db, tenant_id)  # commit() resetea app.tenant_id (ver app/db/rls.py)

        diagnostico = db.get(DiagnosticoTramite, diagnostico_tramite_id)
        tenant = db.get(Tenant, tenant_id)
        tramite = db.get(Tramite, diagnostico.tramite_id) if diagnostico is not None else None
        if diagnostico is None or tenant is None or tramite is None:
            job.estado = "failed"
            job.intentos += 1
            db.commit()
            return

        namespace_efectivo = _namespace_efectivo(db, tenant_id, diagnostico.respuestas, tramite.tipo)
        override = resolver_override(tenant)  # BYOK: credencial propia del tenant si existe
        modo, contenido, verificado = _generar_contenido_y_modo(
            namespace_efectivo,
            tenant.pais,
            tramite.tipo,
            tramite.descripcion,
            tenant.nivel_gobierno,
            override=override,
        )

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
        _registrar_plan_generado(db, tenant_id=tenant_id, tramite=tramite, plan=plan)

        tramite.estado = "plan_listo"

        job.estado = "done"
        db.commit()
    except Exception:
        db.rollback()
        fijar_contexto_tenant(db, tenant_id)  # rollback() también resetea app.tenant_id
        job = db.get(Job, job_id)
        if job is not None:
            job.intentos += 1
            if job.intentos >= LIMITE_INTENTOS:
                # El trámite no puede quedar colgado esperando un intento que nunca llega.
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
    scheduler ni cron). Cubre 2 casos de job sin terminar: `failed` (ya
    incrementó `intentos` en el `except`, solo hay que redisparar) y `running`
    obsoleto por más de `settings.job_umbral_obsoleto_minutos` (el proceso murió
    a medio job, acá se incrementa por primera vez). En ambos, si ya se alcanzó
    `LIMITE_INTENTOS`, se fuerza el degradado en vez de redisparar (evita un
    ciclo infinito).

    `True` = el llamador debe encolar `ejecutar_generacion_plan` vía
    `BackgroundTasks`. `False` = ya se resolvió acá mismo, o no hay nada que hacer.
    """
    if job.diagnostico_tramite_id is None:
        return False

    if job.estado == "failed":
        if job.intentos >= LIMITE_INTENTOS:
            # Ya se alcanzó el límite pero quedó en `failed` (no pudo persistir el
            # degradado antes) -- reintenta el degradado en vez de redisparar, para
            # no entrar en un ciclo failed -> pending -> failed indefinido.
            if _persistir_plan_degradado(db, tenant_id, job.diagnostico_tramite_id):
                job.estado = "done"
            else:
                job.estado = "failed"
            db.commit()
            fijar_contexto_tenant(db, tenant_id)  # commit() resetea app.tenant_id
            return False

        job.estado = "pending"
        db.commit()
        fijar_contexto_tenant(db, tenant_id)
        return True

    if job.estado == "pending" and _esta_obsoleto(job.updated_at, settings.job_umbral_obsoleto_minutos):
        job.intentos += 1  # nunca arrancó (proceso murió justo tras crearlo) -- cuenta como intento fallido
        if job.intentos >= LIMITE_INTENTOS:
            if _persistir_plan_degradado(db, tenant_id, job.diagnostico_tramite_id):
                job.estado = "done"
            else:
                job.estado = "failed"
            db.commit()
            fijar_contexto_tenant(db, tenant_id)
            return False

        db.commit()
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
            fijar_contexto_tenant(db, tenant_id)
            return False

        job.estado = "pending"
        db.commit()
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

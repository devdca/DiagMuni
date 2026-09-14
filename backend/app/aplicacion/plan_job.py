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
from app.dominio.resumen_plan import calcular_orden_sugerido, calcular_resumen_inversion, calcular_resumen_personal
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


def _namespace_efectivo(db: Session, tenant_id: UUID, respuestas: dict, tipo_tramite: str) -> dict:
    """Fusión `{**contexto_institucional_del_tenant, **respuestas_del_tramite}`
    (entregables/fase-2/variables-contexto-institucional.md, sección 3.1, punto 2)
    -- así `autoridad_gobernanza_digital` puede evaluarse como brecha transversal
    junto a las 6 variables ya existentes del trámite, sin colisión de nombres
    entre ambos namespaces. Si el tenant todavía no tiene fila de
    `contexto_institucional`, el campo simplemente no aparece en el dict fusionado
    -- `criterio_se_cumple` (app/engine/reglas_loader.py) ya maneja una clave
    ausente sin fallar (`dict.get` devuelve `None`, nunca lanza `KeyError`).

    Al final se completan las variables que `tipo_tramite` no pregunta -- así ni
    el índice ni el plan las tratan como brecha real (ver
    app/engine/tipos_tramite_loader.py)."""
    contexto = db.execute(
        select(ContextoInstitucional).where(ContextoInstitucional.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if contexto is None:
        namespace = dict(respuestas)
    else:
        namespace_contexto = {
            "poblacion_total": contexto.poblacion_total,
            "personal_total_gobierno": contexto.personal_total_gobierno,
            "presupuesto_tic_anual": contexto.presupuesto_tic_anual,
            "area_tic_existe": contexto.area_tic_existe,
            "conectividad": contexto.conectividad,
            "normativa_local_emitida": contexto.normativa_local_emitida,
            "autoridad_gobernanza_digital": contexto.autoridad_gobernanza_digital,
            "agenda_simplificacion_publicada": contexto.agenda_simplificacion_publicada,
            "portal_datos_abiertos_existe": contexto.portal_datos_abiertos_existe,
            "linea_atencion_ciudadana_centralizada": contexto.linea_atencion_ciudadana_centralizada,
            "capacitacion_personal_tic_anual": contexto.capacitacion_personal_tic_anual,
            "protocolo_ciberseguridad_existe": contexto.protocolo_ciberseguridad_existe,
            "presupuesto_total_anual": contexto.presupuesto_total_anual,
            "numero_tramites_totales": contexto.numero_tramites_totales,
            "ingresos_propios_porcentaje": contexto.ingresos_propios_porcentaje,
            "numero_oficinas_atencion": contexto.numero_oficinas_atencion,
            "enlace_notificado_formalmente": contexto.enlace_notificado_formalmente,
            "convenio_colaboracion_estado": contexto.convenio_colaboracion_estado,
        }
        namespace = {**namespace_contexto, **respuestas}

    return completar_respuestas_no_aplicables(tipo_tramite, namespace)


def _con_brechas_adicionales(contenido: dict, tipo_tramite: str, respuestas: dict) -> dict:
    """Agrega las brechas propias del tipo de trámite (app/engine/
    tipos_tramite_loader.py) al `contenido` ya generado -- determinista, nunca
    pasa por el LLM, para no depender de que el modelo conozca estas fuentes
    normativas nuevas. `"generico"` (o cualquier tipo sin variables_adicionales)
    no agrega nada, así que llamar esto con el default es un no-op seguro."""
    brechas_adicionales = evaluar_brechas_adicionales(tipo_tramite, respuestas)
    if not brechas_adicionales:
        return contenido
    brechas = [*contenido["brechas"], *brechas_adicionales]
    resumen = f"Se detectaron {len(brechas)} brecha(s) de modernización. Ver detalle de cada una a continuación."
    return {**contenido, "brechas": brechas, "resumen_narrativo": resumen}


def _con_sugerencia_libre(
    contenido: dict, descripcion: str, respuestas: dict, pais: str, *, override: OverrideLlmTenant | None = None
) -> dict:
    """Agrega la sugerencia libre (app/adaptadores/llm/sugerencia_libre.py)
    generada a partir de la descripción del trámite -- complementaria a las
    brechas verificadas de arriba, nunca las reemplaza ni pasa por el
    verificador F9 (ver docstring de ese módulo). `sugerencia_libre` queda en
    `None` si no hay descripción o no hay ninguna ruta de LLM disponible -- a
    diferencia del resto del plan, no tiene fallback determinista. `override`
    (BYOK): credencial/preferencia propia del tenant."""
    return {
        **contenido,
        "sugerencia_libre": generar_sugerencia_libre(descripcion, respuestas, pais, override=override),
    }


def _con_estimacion_recursos(
    contenido: dict, respuestas: dict, pais: str, *, override: OverrideLlmTenant | None = None
) -> dict:
    """Agrega la estimación aproximada de personal/presupuesto (app/adaptadores/
    llm/estimacion_recursos.py) -- mismo criterio que `_con_sugerencia_libre`:
    texto libre de IA, sin verificador F9, `None` sin brechas o sin ruta de LLM."""
    return {
        **contenido,
        "estimacion_recursos": generar_estimacion_recursos(
            contenido["brechas"], respuestas, pais, override=override
        ),
    }


def _con_resumen(contenido: dict, respuestas: dict, pais: str) -> dict:
    """Agrega la síntesis determinista de presupuesto, personal y orden sugerido
    (app/engine/resumen_plan.py) -- se calcula sobre `contenido["brechas"]` ya
    completo (incluidas las brechas adicionales del tipo de trámite), nunca antes."""
    brechas = contenido["brechas"]
    return {
        **contenido,
        "resumen_inversion": calcular_resumen_inversion(brechas, pais),
        "resumen_personal": calcular_resumen_personal(brechas, respuestas, pais),
        "orden_sugerido": calcular_orden_sugerido(brechas),
    }


def _generar_contenido_y_modo(
    respuestas: dict,
    pais: str,
    tipo_tramite: str = "generico",
    descripcion: str = "",
    *,
    override: OverrideLlmTenant | None = None,
) -> tuple[str, dict, bool]:
    """Devuelve `(modo, contenido, verificado)` -- `verificado` siempre `True`.
    `override` (BYOK, ver app/aplicacion/preferencia_modelo_ia.py): credencial y
    preferencia propia del tenant, gana sobre cualquier config global del
    operador -- ver app/adaptadores/llm/config.py::obtener_proveedor_llm."""
    rutas_generacion = obtener_rutas_generacion(override=override)
    if not any(esta_disponible(nombre, override=override) for nombre in rutas_generacion):
        contenido = generar_contenido_degradado(respuestas, pais)
        contenido = _con_brechas_adicionales(contenido, tipo_tramite, respuestas)
        contenido = _con_resumen(contenido, respuestas, pais)
        contenido = _con_sugerencia_libre(contenido, descripcion, respuestas, pais, override=override)
        return "degradado", _con_estimacion_recursos(contenido, respuestas, pais, override=override), True

    contenido_llm = generar_contenido_llm(respuestas, pais, override=override)
    contenido_determinista = generar_contenido_degradado(respuestas, pais)
    contexto_gobierno = formatear_contexto_gobierno(respuestas, pais)

    if verificar_contenido(contenido_llm, contenido_determinista, contexto_gobierno, override=override):
        contenido = _con_brechas_adicionales(contenido_llm, tipo_tramite, respuestas)
        contenido = _con_resumen(contenido, respuestas, pais)
        contenido = _con_sugerencia_libre(contenido, descripcion, respuestas, pais, override=override)
        return "llm", _con_estimacion_recursos(contenido, respuestas, pais, override=override), True

    # verificar_contenido ya es fail-closed (rechazo, fallo o no disponible = no
    # aprobado); en cualquier caso se descarta el LLM y se persiste el determinista.
    contenido = _con_brechas_adicionales(contenido_determinista, tipo_tramite, respuestas)
    contenido = _con_resumen(contenido, respuestas, pais)
    contenido = _con_sugerencia_libre(contenido, descripcion, respuestas, pais, override=override)
    return "degradado", _con_estimacion_recursos(contenido, respuestas, pais, override=override), True


def _registrar_plan_generado(db: Session, *, tenant_id: UUID, tramite: Tramite, plan: PlanModernizacion) -> None:
    """Historial persistido (pantalla "Historial") + notificación (campana) del
    evento "se generó un plan" -- un único punto llamado desde los dos lugares que
    pueden terminar en un `PlanModernizacion` nuevo (`_persistir_plan_degradado` y
    el camino feliz de `ejecutar_generacion_plan`), para no repetir el texto ni
    arriesgar que uno de los dos caminos se quede sin avisar."""
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
    """Genera y persiste el plan en modo degradado y cierra el trámite -- mismo
    patrón de versionado y transición de estado que el camino feliz de
    `ejecutar_generacion_plan`, sin intentar la ruta LLM. Devuelve `False` sin
    persistir nada si el diagnóstico o el tenant ya no existen. No hace commit --
    lo hace quien la invoca."""
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

    # BYOK (app/aplicacion/preferencia_modelo_ia.py): este camino nunca intenta la
    # ruta LLM para las brechas del catálogo (siempre genera degradado a
    # propósito), pero `_con_sugerencia_libre`/`_con_estimacion_recursos` sí son
    # texto libre de IA -- si el tenant configuró su propia credencial, la usan.
    override = resolver_override(tenant)
    namespace_efectivo = _namespace_efectivo(db, tenant_id, diagnostico.respuestas, tramite.tipo)
    contenido = _con_brechas_adicionales(
        generar_contenido_degradado(namespace_efectivo, tenant.pais), tramite.tipo, namespace_efectivo
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
        # commit() termina la transacción y con ella el app.tenant_id local (ver
        # app/db/rls.py) — hay que volver a fijarlo antes de la siguiente consulta.
        fijar_contexto_tenant(db, tenant_id)

        diagnostico = db.get(DiagnosticoTramite, diagnostico_tramite_id)
        tenant = db.get(Tenant, tenant_id)
        tramite = db.get(Tramite, diagnostico.tramite_id) if diagnostico is not None else None
        if diagnostico is None or tenant is None or tramite is None:
            job.estado = "failed"
            job.intentos += 1
            db.commit()
            return

        namespace_efectivo = _namespace_efectivo(db, tenant_id, diagnostico.respuestas, tramite.tipo)
        # BYOK (app/aplicacion/preferencia_modelo_ia.py): la credencial/preferencia
        # propia de este gobierno, si la configuró -- gana sobre LLM_PROVIDER
        # global y sobre cualquier key del operador.
        override = resolver_override(tenant)
        modo, contenido, verificado = _generar_contenido_y_modo(
            namespace_efectivo, tenant.pais, tramite.tipo, tramite.descripcion, override=override
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

    if job.estado == "pending" and _esta_obsoleto(job.updated_at, settings.job_umbral_obsoleto_minutos):
        # nunca llegó a arrancar (ej. el proceso murió justo tras crear el job,
        # antes de que corriera el BackgroundTask) -- se cuenta como un intento
        # fallido igual que un `running` obsoleto, para no redisparar sin límite.
        job.intentos += 1
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

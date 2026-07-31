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

from uuid import UUID

from sqlalchemy import select

from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.engine.plantillas import generar_contenido_degradado
from app.ia.config import esta_disponible
from app.ia.generador_plan import generar_contenido_llm
from app.ia.verificador import verificar_contenido
from app.models import DiagnosticoTramite, Job, PlanModernizacion, Tenant, Tramite

# Ruta que generador_plan.py usa para redactar -- si no está disponible, no hay
# nada que generar vía LLM.
_RUTA_GENERACION = "calidad"


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
            job.estado = "failed"
            db.commit()
        raise
    finally:
        db.close()

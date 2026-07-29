"""Job asíncrono de generación de plan (docs/TRD.md, "Job asíncrono — ciclo de vida").

Fase D2 de docs/plan-implementacion.md: dispara la generación **en modo degradado
únicamente** (motor determinista, engine/plantillas.py) — la fase E (LLM, F3 real)
reemplaza el cuerpo de este job más adelante sin tocar su contrato (tabla job,
estados pending/running/done/failed).
"""

from uuid import UUID

from sqlalchemy import select

from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.engine.plantillas import generar_contenido_degradado
from app.models import DiagnosticoTramite, Job, PlanModernizacion, Tenant, Tramite


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

        contenido = generar_contenido_degradado(diagnostico.respuestas, tenant.pais)

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
            contenido=contenido,
            # Sin LLM en el camino (fase E aún no existe), no hay nada que F9 verifique
            # contra el catálogo — el contenido ya viene directo de engine/, correcto
            # por construcción (docs/backend-schema.md, campo verificado).
            verificado=True,
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

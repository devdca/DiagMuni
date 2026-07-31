"""Job asíncrono de generación de plan (docs/TRD.md, "Job asíncrono — ciclo de vida").

Fase D2 de docs/plan-implementacion.md disparaba la generación **en modo degradado
únicamente** (motor determinista, engine/plantillas.py). Fase E3
(docs/plan-implementacion.md, fila E3: "Verificador (F9): audita la salida de E2
contra el `contenido` estructurado antes de marcar `verificado=true`; si falla, el
plan se muestra en modo degradado (fase C), nunca sin verificar") reemplaza el
cuerpo de este job para integrar el generador LLM (E2, `app.ia.generador_plan`) y el
verificador (E3, `app.ia.verificador`) -- sin tocar su contrato (tabla job, estados
pending/running/done/failed, ni el mecanismo de `job.intentos` para crashes de
ejecución, ver el bloque `try/except` de `ejecutar_generacion_plan`).

Conciliación de dos fuentes en apariencia contradictorias -- léelo antes de tocar
`_generar_contenido_y_modo`:
- docs/backend-schema.md, campo `verificado`: "`false` bloquea la vista y reintenta,
  nunca se muestra un plan no verificado".
- docs/plan-implementacion.md, fila E3: si la verificación falla, el plan "se
  muestra en modo degradado ... nunca sin verificar".
La lectura que concilia ambas, implementada abajo: **nunca se persiste
`verificado=False`**. Dentro de la misma ejecución del job, el contenido y el modo
se deciden así:
  1. Si la ruta `calidad` (la que usa E2 para generar) no está disponible -> se
     genera directo con `generar_contenido_degradado` (modo `degradado`,
     `verificado=True`) -- el verificador ni se invoca, porque no hay nada LLM que
     auditar.
  2. Si se generó contenido LLM y el verificador (ruta `economico`) lo aprueba ->
     se persiste ese contenido (modo `llm`, `verificado=True`).
  3. Si el verificador lo rechaza, o el verificador mismo falla / no está
     disponible / da timeout (`app.ia.verificador.verificar_contenido` ya trata
     todo eso como "no aprobado", nunca asume éxito por defecto) -> se descarta el
     contenido LLM y se persiste el contenido determinista (modo `degradado`,
     `verificado=True`).
El plan que se guarda SIEMPRE tiene `verificado=True` -- sea porque pasó la
auditoría LLM (modo `llm`) o porque es determinista por construcción (modo
`degradado`). Así "nunca se muestra un plan no verificado" se cumple literalmente,
sin necesitar un mecanismo de reintento aparte del que ya existe para crashes
(`job.intentos`, mecanismo separado, no tocado por este cambio).

Nota de diseño: la decisión de qué contenido/modo generar vive en
`_generar_contenido_y_modo`, una función pura (sin sesión de base de datos) para
poder testearla sin depender de una instancia de Postgres real -- el resto del job
(`ejecutar_generacion_plan`) sigue siendo el único responsable de la sesión, la
tabla `job` y sus estados.
"""

from uuid import UUID

from sqlalchemy import select

from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.engine.plantillas import generar_contenido_degradado
from app.ia.config import esta_disponible
from app.ia.generador_plan import generar_contenido_llm
from app.ia.verificador import verificar_contenido
from app.models import DiagnosticoTramite, Job, PlanModernizacion, Tenant, Tramite

# Ruta que E2 (generador_plan.py) usa para redactar -- ver docs/TRD.md, "F3
# (generador de plan) usa `calidad` (Claude)". Se referencia acá (y no un nombre
# genérico) para dejar explícito por qué, si esta ruta no está disponible, no tiene
# sentido intentar generar contenido LLM en absoluto.
_RUTA_GENERACION = "calidad"


def _generar_contenido_y_modo(respuestas: dict, pais: str) -> tuple[str, dict, bool]:
    """Decide qué contenido y qué modo persistir para un diagnóstico dado,
    conforme al flujo descrito en el docstring del módulo. Devuelve
    `(modo, contenido, verificado)` -- `verificado` es SIEMPRE `True`: los tres
    caminos posibles (sin ruta de generación, LLM aprobado, LLM rechazado/no
    verificable) terminan en un plan seguro de mostrar, nunca en `verificado=False`.
    """
    if not esta_disponible(_RUTA_GENERACION):
        # Sin ruta de generación LLM disponible: no hay nada que redactar vía LLM y,
        # por lo tanto, nada que F9 audite -- se genera directo en modo degradado
        # (docs/plan-implementacion.md, fila E3, primer camino).
        return "degradado", generar_contenido_degradado(respuestas, pais), True

    contenido_llm = generar_contenido_llm(respuestas, pais)
    contenido_determinista = generar_contenido_degradado(respuestas, pais)

    if verificar_contenido(contenido_llm, contenido_determinista):
        return "llm", contenido_llm, True

    # El verificador rechazó el contenido, o el verificador mismo falló / no
    # estaba disponible / dio timeout -- `verificar_contenido` ya encapsula ese
    # sesgo (fail-closed, nunca asume éxito por defecto). En cualquiera de esos
    # casos se descarta el contenido LLM y se persiste el determinista.
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
            # `verificado` siempre True en este punto -- ver docstring del módulo y
            # de `_generar_contenido_y_modo` (docs/backend-schema.md, campo
            # verificado: "nunca se muestra un plan no verificado").
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

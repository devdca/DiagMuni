from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TokenData, get_current_token, get_db
from app.core.audit_log import registrar_diagnostico_enviado
from app.core.rate_limit import LimitadorVentanaDeslizante
from app.db.rls import fijar_contexto_tenant
from app.engine.madurez import VERSION_MOTOR, calcular_indice_madurez
from app.jobs.plan_job import ejecutar_generacion_plan, obtener_job_vigente, revisar_job_obsoleto
from app.models import DiagnosticoTramite, Job, Tramite
from app.schemas.diagnostico import (
    MECANISMOS_IDENTIDAD_VALIDOS,
    DiagnosticoEnviar,
    DiagnosticoGuardar,
    DiagnosticoOut,
)

router = APIRouter(prefix="/api/tramites", tags=["diagnostico"])

# Cooldown propio de este endpoint -- la generación de plan es la única operación
# con costo real de LLM (auditoría de seguridad H-11); el chequeo de job vigente
# de abajo solo evita duplicados concurrentes, esto acota además cuántas
# generaciones nuevas se pueden disparar una vez que la anterior ya terminó.
#
# Dos llaves a propósito, porque una sola no cubre los dos casos:
#
# - Por (usuario, trámite): acota la regeneración del plan de un mismo trámite,
#   que es donde está el costo repetido. Llavear solo por usuario rompe el flujo
#   real del producto -- un funcionario captura el catálogo de trámites de su
#   municipio (decenas) de una sentada y toparía el límite al sexto trámite,
#   aunque cada envío sea legítimo y de un trámite distinto.
# - Por usuario, con un techo muy por encima de cualquier captura manual: acota
#   el total que un script o una cuenta comprometida puede disparar recorriendo
#   muchos trámites, que la llave por trámite sola no limita.
INTENTOS_MAXIMOS_POR_TRAMITE = 5
INTENTOS_MAXIMOS_POR_USUARIO = 60
VENTANA_SEGUNDOS = 300.0

_limitador_tramite = LimitadorVentanaDeslizante(INTENTOS_MAXIMOS_POR_TRAMITE, VENTANA_SEGUNDOS)
_limitador_usuario = LimitadorVentanaDeslizante(INTENTOS_MAXIMOS_POR_USUARIO, VENTANA_SEGUNDOS)


def _validar_mecanismo_identidad(respuestas: dict) -> None:
    """`mecanismo_identidad` es opcional -- un funcionario a media captura puede no
    haber llegado todavía a esa pregunta -- pero si la clave está presente, su
    valor debe ser uno de los 4 catalogados (docs/ux-brief.md línea 71: nunca se
    guarda un "otro" sin resolver ni ningún otro texto libre). Se valida acá y no
    con un validador de Pydantic en el schema para poder responder con el mismo
    formato de `detail` (string plano) que ya usa el resto de esta API para los
    404, en vez de la lista de objetos que arma Pydantic para sus propios errores
    de validación.

    Se llama tanto desde guardar_diagnostico como desde enviar_diagnostico: la
    regla dice "nunca se guarde", y "Guardar y continuar después" persiste
    `respuestas` en la base igual que el envío final, no es un borrador en
    memoria del cliente."""
    valor = respuestas.get("mecanismo_identidad")
    if valor is not None and valor not in MECANISMOS_IDENTIDAD_VALIDOS:
        opciones = ", ".join(sorted(MECANISMOS_IDENTIDAD_VALIDOS))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"El mecanismo de identidad {valor!r} no es una opción válida. "
                f"Elija una de las opciones del formulario: {opciones}."
            ),
        )


def _obtener_o_crear_diagnostico(db: Session, tenant_id: UUID, tramite_id: UUID) -> DiagnosticoTramite:
    diagnostico = db.execute(
        select(DiagnosticoTramite).where(DiagnosticoTramite.tramite_id == tramite_id)
    ).scalar_one_or_none()
    if diagnostico is None:
        diagnostico = DiagnosticoTramite(tramite_id=tramite_id, tenant_id=tenant_id, respuestas={})
        db.add(diagnostico)
        db.flush()
    return diagnostico


@router.get("/{tramite_id}/diagnostico", response_model=DiagnosticoOut)
def obtener_diagnostico(tramite_id: UUID, db: Annotated[Session, Depends(get_db)]) -> DiagnosticoTramite:
    diagnostico = db.execute(
        select(DiagnosticoTramite).where(DiagnosticoTramite.tramite_id == tramite_id)
    ).scalar_one_or_none()
    if diagnostico is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnóstico no iniciado")
    return diagnostico


@router.put("/{tramite_id}/diagnostico", response_model=DiagnosticoOut)
def guardar_diagnostico(
    tramite_id: UUID,
    payload: DiagnosticoGuardar,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> DiagnosticoTramite:
    """'Guardar y continuar después' (docs/app-flow.md) — no calcula índice ni dispara plan."""
    _validar_mecanismo_identidad(payload.respuestas)
    tramite = db.get(Tramite, tramite_id)
    if tramite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trámite no encontrado")

    diagnostico = _obtener_o_crear_diagnostico(db, token.tenant_id, tramite_id)
    diagnostico.respuestas = payload.respuestas
    if tramite.estado != "en_progreso":
        tramite.estado = "en_progreso"
    db.commit()
    # commit() termina la transacción y con ella el app.tenant_id local (ver
    # app/db/rls.py) -- hay que volver a fijarlo antes de la siguiente consulta con
    # RLS en esta misma sesión.
    fijar_contexto_tenant(db, token.tenant_id)
    return diagnostico


@router.post("/{tramite_id}/diagnostico/enviar", response_model=DiagnosticoOut)
def enviar_diagnostico(
    tramite_id: UUID,
    payload: DiagnosticoEnviar,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> DiagnosticoTramite:
    """Envío completo: F2 (índice, síncrono y determinista) + dispara automáticamente
    el job de plan (docs/app-flow.md, máquina de estados: diagnosticado -> generando_plan,
    nunca requiere una acción manual adicional)."""
    permitido = _limitador_tramite.permitir_intento(
        f"{token.usuario_id}:{tramite_id}"
    ) and _limitador_usuario.permitir_intento(str(token.usuario_id))
    if not permitido:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados envíos seguidos. Espera unos minutos e intenta de nuevo.",
        )

    _validar_mecanismo_identidad(payload.respuestas)
    tramite = db.get(Tramite, tramite_id)
    if tramite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trámite no encontrado")

    diagnostico = _obtener_o_crear_diagnostico(db, token.tenant_id, tramite_id)

    # Ya hay una generación en curso para este trámite: si el job vigente quedó
    # obsoleto (el proceso murió a medio camino) se redispara ese mismo job en
    # vez de crear uno nuevo. Si sigue vivo se rechaza con 409, que es lo único
    # honesto de las tres opciones: guardar aquí las respuestas nuevas dejaría
    # al plan en generación describiendo un diagnóstico que ya cambió, y
    # descartarlas devolviendo 200 le haría creer al funcionario que se
    # guardaron. Con el 409 el cliente conserva su captura y reintenta cuando
    # el plan termine.
    job_vigente = obtener_job_vigente(db, diagnostico.id)
    job_a_redisparar = None
    if job_vigente is not None and job_vigente.estado in ("pending", "running"):
        if revisar_job_obsoleto(db, token.tenant_id, job_vigente):
            job_a_redisparar = job_vigente
        elif job_vigente.estado in ("pending", "running"):
            # `revisar_job_obsoleto` devuelve False también cuando cerró el job
            # al agotar LIMITE_INTENTOS (lo deja en done/failed) -- en ese caso
            # no queda nada en curso y el envío sigue su camino normal.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "El plan de este trámite se está generando. "
                    "Espera a que termine para reenviar el diagnóstico."
                ),
            )

    diagnostico.respuestas = payload.respuestas
    diagnostico.indice_madurez = calcular_indice_madurez(payload.respuestas)
    diagnostico.version_motor = VERSION_MOTOR
    diagnostico.completado_en = datetime.now(UTC)

    if job_a_redisparar is not None:
        job = job_a_redisparar
    else:
        job = Job(tenant_id=token.tenant_id, tipo="generacion_plan", diagnostico_tramite_id=diagnostico.id)
        db.add(job)
    tramite.estado = "generando_plan"
    db.commit()
    # mismo motivo que el commit de guardar_diagnostico -- refijar antes de la
    # siguiente consulta con RLS en esta misma sesión.
    fijar_contexto_tenant(db, token.tenant_id)

    background_tasks.add_task(ejecutar_generacion_plan, job.id, token.tenant_id, diagnostico.id)

    # Log de auditoría (docs/plan-implementacion.md Fase G2) -- después del commit,
    # con los mismos valores ya persistidos, nunca antes de confirmar la transacción.
    registrar_diagnostico_enviado(
        tenant_id=token.tenant_id,
        usuario_id=token.usuario_id,
        tramite_id=tramite_id,
        diagnostico_id=diagnostico.id,
        indice_madurez=diagnostico.indice_madurez,
        version_motor=diagnostico.version_motor,
        job_id=job.id,
    )

    return diagnostico

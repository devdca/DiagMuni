from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adaptadores.http.deps import TokenData, get_current_token, get_db
from app.aplicacion.historial import TIPO_DIAGNOSTICO_CORREGIDO, TIPO_DIAGNOSTICO_ENVIADO, registrar_evento
from app.aplicacion.historial_indice_global import registrar_snapshot_indice_global
from app.aplicacion.plan_job import ejecutar_generacion_plan, obtener_job_vigente, revisar_job_obsoleto
from app.core.audit_log import registrar_diagnostico_enviado
from app.core.rate_limit import LimitadorVentanaDeslizante
from app.db.rls import fijar_contexto_tenant
from app.dominio.madurez import VERSION_MOTOR, calcular_indice_madurez
from app.dominio.tipos_tramite_loader import completar_respuestas_no_aplicables
from app.models import DiagnosticoTramite, Job, Tramite
from app.schemas.diagnostico import (
    MECANISMOS_IDENTIDAD_VALIDOS,
    DiagnosticoEnviar,
    DiagnosticoGuardar,
    DiagnosticoOut,
    SimulacionOut,
)

router = APIRouter(prefix="/api/tramites", tags=["diagnostico"])

# Cooldown de envíos (hallazgo H-11): por trámite, para acotar regeneraciones
# repetidas del mismo plan; por usuario, con techo alto, para acotar un script o
# cuenta comprometida recorriendo muchos trámites.
INTENTOS_MAXIMOS_POR_TRAMITE = 5
INTENTOS_MAXIMOS_POR_USUARIO = 60
VENTANA_SEGUNDOS = 300.0

_limitador_tramite = LimitadorVentanaDeslizante(INTENTOS_MAXIMOS_POR_TRAMITE, VENTANA_SEGUNDOS)
_limitador_usuario = LimitadorVentanaDeslizante(INTENTOS_MAXIMOS_POR_USUARIO, VENTANA_SEGUNDOS)


def _validar_mecanismo_identidad(respuestas: dict) -> None:
    """Opcional, pero si viene debe ser una de las 4 opciones catalogadas -- nunca
    se guarda un "otro" sin resolver (docs/ux-brief.md línea 71). Validado a mano,
    no con Pydantic, para responder con el mismo `detail` en texto plano que el
    resto de la API."""
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
    # commit() resetea app.tenant_id (ver app/db/rls.py) -- refijar para la sesión.
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

    # Si ya hay un job vigente y obsoleto (proceso murió a medio camino) se
    # redispara; si sigue vivo se rechaza con 409 -- guardar o descartar aquí
    # dejaría el plan describiendo un diagnóstico ya cambiado, o mentiría con un
    # 200 sin guardar. El cliente conserva su captura y reintenta después.
    job_vigente = obtener_job_vigente(db, diagnostico.id)
    job_a_redisparar = None
    if job_vigente is not None and job_vigente.estado in ("pending", "running"):
        if revisar_job_obsoleto(db, token.tenant_id, job_vigente):
            job_a_redisparar = job_vigente
        elif job_vigente.estado in ("pending", "running"):
            # False también cuando el job cerró por agotar LIMITE_INTENTOS.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "El plan de este trámite se está generando. "
                    "Espera a que termine para reenviar el diagnóstico."
                ),
            )

    # Variables no aplicables se completan como "satisfechas" solo para el índice;
    # lo persistido en `diagnostico.respuestas` sigue siendo lo que el funcionario contestó.
    respuestas_efectivas = completar_respuestas_no_aplicables(tramite.tipo, payload.respuestas)

    # Capturado antes de sobreescribir completado_en -- distingue primer envío de corrección
    # (docs/app-flow.md) para la línea de tiempo de "Historial".
    es_correccion = diagnostico.completado_en is not None

    diagnostico.respuestas = payload.respuestas
    diagnostico.indice_madurez = calcular_indice_madurez(respuestas_efectivas)
    diagnostico.version_motor = VERSION_MOTOR
    diagnostico.completado_en = datetime.now(UTC)

    if job_a_redisparar is not None:
        job = job_a_redisparar
    else:
        job = Job(tenant_id=token.tenant_id, tipo="generacion_plan", diagnostico_tramite_id=diagnostico.id)
        db.add(job)
    tramite.estado = "generando_plan"

    registrar_evento(
        db,
        tenant_id=token.tenant_id,
        tramite_id=tramite_id,
        usuario_id=token.usuario_id,
        tipo=TIPO_DIAGNOSTICO_CORREGIDO if es_correccion else TIPO_DIAGNOSTICO_ENVIADO,
        descripcion=(
            f"Diagnóstico corregido -- índice recalculado a {diagnostico.indice_madurez}."
            if es_correccion
            else f"Diagnóstico enviado -- índice de madurez calculado: {diagnostico.indice_madurez}."
        ),
        metadatos={"indice_madurez": diagnostico.indice_madurez, "version_motor": diagnostico.version_motor},
    )
    # Punto de la gráfica de tendencia (migración 0015) -- mismo commit que el envío.
    registrar_snapshot_indice_global(db, tenant_id=token.tenant_id)

    db.commit()
    fijar_contexto_tenant(db, token.tenant_id)  # commit() resetea app.tenant_id

    background_tasks.add_task(ejecutar_generacion_plan, job.id, token.tenant_id, diagnostico.id)

    # Auditoría (Fase G2) después del commit, con los valores ya persistidos.
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


@router.post("/{tramite_id}/diagnostico/simular", response_model=SimulacionOut)
def simular_diagnostico(
    tramite_id: UUID,
    payload: DiagnosticoGuardar,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> SimulacionOut:
    """"Qué pasa si" -- corre el motor determinista sobre `respuestas` sin guardar
    nada ni tocar `job`/`tramite.estado`. Mismo cálculo que `enviar_diagnostico`."""
    _validar_mecanismo_identidad(payload.respuestas)
    tramite = db.get(Tramite, tramite_id)
    if tramite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trámite no encontrado")

    diagnostico_actual = db.execute(
        select(DiagnosticoTramite).where(DiagnosticoTramite.tramite_id == tramite_id)
    ).scalar_one_or_none()
    indice_actual = diagnostico_actual.indice_madurez if diagnostico_actual is not None else None

    respuestas_efectivas = completar_respuestas_no_aplicables(tramite.tipo, payload.respuestas)
    indice_proyectado = calcular_indice_madurez(respuestas_efectivas)

    return SimulacionOut(indice_actual=indice_actual, indice_proyectado=indice_proyectado)

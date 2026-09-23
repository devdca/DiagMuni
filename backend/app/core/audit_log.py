"""Log de auditoría en JSON a stdout: un evento por envío completo de
diagnóstico (no por "Guardar y continuar después", que es borrador) y por
cambio de ciclo de vida de un trámite. stdlib `logging` puro, sin dependencia
nueva solo para formatear JSON.

Hasta que exista un reporte propio, es la única fuente de la métrica "trámites
diagnosticados" del PRD -- contar líneas `"evento": "diagnostico_enviado"`.

Append-only: `tramite_eliminado` nunca borra ni reescribe la línea
`diagnostico_enviado` previa de ese trámite."""

import json
import logging
import sys
from datetime import UTC, datetime
from uuid import UUID

logger = logging.getLogger("diagmuni.auditoria")
if not logger.handlers:  # evita duplicar la línea si el módulo se importa más de una vez
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


def registrar_diagnostico_enviado(
    *,
    tenant_id: UUID,
    usuario_id: UUID,
    tramite_id: UUID,
    diagnostico_id: UUID,
    indice_madurez: int,
    version_motor: str,
    job_id: UUID,
) -> None:
    """Llamar tras confirmar el envío en `enviar_diagnostico` -- todos los
    valores ya están resueltos ahí."""
    logger.info(
        json.dumps(
            {
                "evento": "diagnostico_enviado",
                "timestamp": datetime.now(UTC).isoformat(),
                "tenant_id": str(tenant_id),
                "usuario_id": str(usuario_id),
                "tramite_id": str(tramite_id),
                "diagnostico_id": str(diagnostico_id),
                "indice_madurez": indice_madurez,
                "version_motor": version_motor,
                "job_id": str(job_id),
            },
            ensure_ascii=False,
        )
    )


def _registrar_evento_tramite(evento: str, *, tenant_id: UUID, usuario_id: UUID, tramite_id: UUID, nombre: str) -> None:
    """Base común de los 3 eventos de trámite -- incluye `nombre` porque en
    `tramite_eliminado` la fila deja de existir sin él."""
    logger.info(
        json.dumps(
            {
                "evento": evento,
                "timestamp": datetime.now(UTC).isoformat(),
                "tenant_id": str(tenant_id),
                "usuario_id": str(usuario_id),
                "tramite_id": str(tramite_id),
                "nombre": nombre,
            },
            ensure_ascii=False,
        )
    )


def registrar_tramite_eliminado(*, tenant_id: UUID, usuario_id: UUID, tramite_id: UUID, nombre: str) -> None:
    """Solo alcanza trámites sin diagnóstico completado."""
    _registrar_evento_tramite(
        "tramite_eliminado", tenant_id=tenant_id, usuario_id=usuario_id, tramite_id=tramite_id, nombre=nombre
    )


def registrar_tramite_archivado(*, tenant_id: UUID, usuario_id: UUID, tramite_id: UUID, nombre: str) -> None:
    """El trámite y su historial siguen existiendo, solo se ocultan de
    panel/índice/seguimiento."""
    _registrar_evento_tramite(
        "tramite_archivado", tenant_id=tenant_id, usuario_id=usuario_id, tramite_id=tramite_id, nombre=nombre
    )


def registrar_tramite_desarchivado(*, tenant_id: UUID, usuario_id: UUID, tramite_id: UUID, nombre: str) -> None:
    _registrar_evento_tramite(
        "tramite_desarchivado", tenant_id=tenant_id, usuario_id=usuario_id, tramite_id=tramite_id, nombre=nombre
    )

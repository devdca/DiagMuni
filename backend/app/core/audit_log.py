"""Log de auditoría del diagnóstico (docs/plan-implementacion.md Fase G2;
docs/stack-tecnologico.md, fila "Observabilidad": logs a stdout + `/health` +
log de auditoría del diagnóstico, "sin stack pesado... para el MVP"). Una
línea JSON a stdout por cada envío completo de diagnóstico -- no por cada
"Guardar y continuar después" (docs/app-flow.md), que es un borrador parcial,
no un evento de diagnóstico completado.

stdlib `logging` puro, sin `structlog` ni `python-json-logger`: ninguna de las
dos está en requirements.txt, y agregar una dependencia solo para formatear
JSON sería el "stack pesado" que docs/stack-tecnologico.md descarta a
propósito (mismo criterio que app/core/rate_limit.py: sin dependencia nueva
cuando la stdlib alcanza).

Hasta que exista un reporte propio, esta es la única fuente de la métrica
"número de trámites diagnosticados" del PRD (docs/PRD.md, "Métricas de éxito
del piloto") -- quien opere el despliegue puede contar líneas
`"evento": "diagnostico_enviado"` en los logs (`docker compose logs backend`)."""

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
    """Llamar justo después de confirmar el envío en `enviar_diagnostico`
    (backend/app/api/diagnosticos.py) -- todos estos valores ya están resueltos
    ahí, ninguno requiere una consulta adicional."""
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

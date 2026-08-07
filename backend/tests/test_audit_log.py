"""Test puro de `app/core/audit_log.py` -- a diferencia de
test_api_diagnosticos.py, no necesita Postgres real: `registrar_diagnostico_enviado`
no toca la base de datos, solo emite una línea de log."""

import json
import logging
from uuid import uuid4

from app.core.audit_log import registrar_diagnostico_enviado


def test_registrar_diagnostico_enviado_emite_una_linea_json_con_los_campos_esperados(caplog):
    tenant_id, usuario_id, tramite_id, diagnostico_id, job_id = (uuid4() for _ in range(5))

    with caplog.at_level(logging.INFO, logger="diagmuni.auditoria"):
        registrar_diagnostico_enviado(
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            tramite_id=tramite_id,
            diagnostico_id=diagnostico_id,
            indice_madurez=2,
            version_motor="2026.1",
            job_id=job_id,
        )

    assert len(caplog.records) == 1
    linea = json.loads(caplog.records[0].message)
    assert linea == {
        "evento": "diagnostico_enviado",
        "timestamp": linea["timestamp"],  # se valida el formato abajo, no el valor exacto
        "tenant_id": str(tenant_id),
        "usuario_id": str(usuario_id),
        "tramite_id": str(tramite_id),
        "diagnostico_id": str(diagnostico_id),
        "indice_madurez": 2,
        "version_motor": "2026.1",
        "job_id": str(job_id),
    }
    # ISO 8601 con offset explícito (datetime.now(UTC).isoformat()) -- quien lea el
    # log necesita poder ordenar/parsear el timestamp sin ambigüedad de zona horaria.
    assert linea["timestamp"].endswith("+00:00")

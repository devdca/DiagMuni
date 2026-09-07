"""Auditoría de seguridad H-05: `respuestas` no tenía ninguna cota de tamaño
propia -- un payload de ~900KB pasaba sin problema (nginx solo bloqueaba a
partir de 1MB, ver H-08). Cubre el límite agregado en app/schemas/diagnostico.py."""

import pytest
from pydantic import ValidationError

from app.schemas.diagnostico import DiagnosticoEnviar, DiagnosticoGuardar


@pytest.mark.parametrize("schema", [DiagnosticoGuardar, DiagnosticoEnviar])
def test_respuestas_normales_se_aceptan(schema):
    instancia = schema(respuestas={"documentos_digitalizados": True, "mecanismo_identidad": "propio"})
    assert instancia.respuestas["documentos_digitalizados"] is True


@pytest.mark.parametrize("schema", [DiagnosticoGuardar, DiagnosticoEnviar])
def test_respuestas_demasiado_grandes_se_rechazan(schema):
    payload_grande = {"relleno": "x" * 200_000}
    with pytest.raises(ValidationError, match="excede el máximo"):
        schema(respuestas=payload_grande)

import json
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

# Fuente de verdad: ETIQUETA_MECANISMO en frontend/src/pages/Diagnostico.tsx
# (docs/ux-brief.md línea 71) -- "otro, especifique" nunca es un valor guardable
# per se, es una bandera de UI para que el funcionario elija/confirme uno de estos
# cuatro antes de habilitar el envío. `respuestas` es un dict genérico (sin tipar
# campo por campo), así que esta validación vive fuera del modelo de campos fijos
# de abajo -- ver app/api/diagnosticos.py para dónde se aplica.
MECANISMOS_IDENTIDAD_VALIDOS = frozenset({"llave_mx", "id_uruguay", "propio", "ninguno"})

# H-05 (auditoría de seguridad): nginx ya limita el body a 1MB (H-08), pero un
# payload de ~900KB en `respuestas` pasaba sin ninguna validación propia de la
# app -- una respuesta real nunca pesa más que unos pocos KB.
_RESPUESTAS_TAMANO_MAXIMO_BYTES = 100_000


class _RespuestasConLimite(BaseModel):
    respuestas: dict

    @field_validator("respuestas")
    @classmethod
    def _limitar_tamano(cls, respuestas: dict) -> dict:
        tamano = len(json.dumps(respuestas))
        if tamano > _RESPUESTAS_TAMANO_MAXIMO_BYTES:
            raise ValueError(
                f"respuestas pesa {tamano} bytes, excede el máximo permitido "
                f"({_RESPUESTAS_TAMANO_MAXIMO_BYTES} bytes)"
            )
        return respuestas


class DiagnosticoGuardar(_RespuestasConLimite):
    """'Guardar y continuar después' (docs/app-flow.md) — respuestas parciales, no
    dispara cálculo de índice ni generación de plan."""


class DiagnosticoEnviar(_RespuestasConLimite):
    """Envío completo — dispara F2 (síncrono) y encola F3 en modo degradado (D2)."""


class DiagnosticoOut(BaseModel):
    id: UUID
    tramite_id: UUID
    respuestas: dict
    indice_madurez: int | None
    version_motor: str | None
    completado_en: datetime | None

    model_config = {"from_attributes": True}

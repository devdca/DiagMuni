import json
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

# "otro, especifique" nunca es un valor guardable -- es una bandera de UI hasta
# que el funcionario confirme uno de estos cuatro.
MECANISMOS_IDENTIDAD_VALIDOS = frozenset({"llave_mx", "id_uruguay", "propio", "ninguno"})

_RESPUESTAS_TAMANO_MAXIMO_BYTES = 100_000  # H-05: una respuesta real nunca pesa más que unos KB


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


class SimulacionOut(BaseModel):
    """Respuesta de POST /api/tramites/{id}/diagnostico/simular -- cálculo del
    motor determinista (F2) sobre respuestas hipotéticas, sin persistir nada.
    `indice_actual` es el índice YA guardado del diagnóstico (`None` si nunca se
    envió); `indice_proyectado` es lo que resultaría de enviar `respuestas` tal
    como están ahora mismo."""

    indice_actual: int | None
    indice_proyectado: int

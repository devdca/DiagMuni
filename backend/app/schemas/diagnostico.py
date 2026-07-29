from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DiagnosticoGuardar(BaseModel):
    """'Guardar y continuar después' (docs/app-flow.md) — respuestas parciales, no
    dispara cálculo de índice ni generación de plan."""

    respuestas: dict


class DiagnosticoEnviar(BaseModel):
    """Envío completo — dispara F2 (síncrono) y encola F3 en modo degradado (D2)."""

    respuestas: dict


class DiagnosticoOut(BaseModel):
    id: UUID
    tramite_id: UUID
    respuestas: dict
    indice_madurez: int | None
    version_motor: str | None
    completado_en: datetime | None

    model_config = {"from_attributes": True}

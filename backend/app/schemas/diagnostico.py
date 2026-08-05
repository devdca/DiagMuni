from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

# Fuente de verdad: ETIQUETA_MECANISMO en frontend/src/pages/Diagnostico.tsx
# (docs/ux-brief.md línea 71) -- "otro, especifique" nunca es un valor guardable
# per se, es una bandera de UI para que el funcionario elija/confirme uno de estos
# cuatro antes de habilitar el envío. `respuestas` es un dict genérico (sin tipar
# campo por campo), así que esta validación vive fuera del modelo de campos fijos
# de abajo -- ver app/api/diagnosticos.py para dónde se aplica.
MECANISMOS_IDENTIDAD_VALIDOS = frozenset({"llave_mx", "id_uruguay", "propio", "ninguno"})


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

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TramiteCreate(BaseModel):
    nombre: str
    descripcion: str = ""


class TramiteOut(BaseModel):
    id: UUID
    nombre: str
    descripcion: str
    estado: str
    created_at: datetime
    updated_at: datetime
    # Tomados de DiagnosticoTramite (sin relación ORM declarada entre Tramite y
    # DiagnosticoTramite -- ver app/api/tramites.py) -- ausentes (None) mientras
    # el trámite no tenga un diagnóstico completo.
    indice_madurez: int | None = None
    completado_en: datetime | None = None
    archivado_en: datetime | None = None

    model_config = {"from_attributes": True}


class PanelResumenOut(BaseModel):
    """Respuesta de GET /api/tramites: la lista de trámites ya extendida arriba,
    más el agregado del panel resumen (docs/ux-brief.md, "2. Panel resumen") --
    el promedio SIEMPRE se calcula con app.engine.madurez.calcular_indice_global,
    nunca reimplementado acá ni en el frontend."""

    tramites: list[TramiteOut]
    indice_global: float | None
    fecha_ultimo_diagnostico: datetime | None

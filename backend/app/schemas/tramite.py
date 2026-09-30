from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.dominio.tipos_tramite_loader import cargar_tipos_tramite


class TramiteCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)  # fuente de verdad del límite; el frontend solo avisa al escribir
    descripcion: str = ""
    tipo: str = "generico"

    @field_validator("tipo")
    @classmethod
    def _tipo_valido(cls, tipo: str) -> str:
        if tipo not in cargar_tipos_tramite():
            raise ValueError(f"tipo de trámite '{tipo}' no está en el catálogo (GET /api/tipos-tramite)")
        return tipo


class TramiteOut(BaseModel):
    id: UUID
    nombre: str
    descripcion: str
    estado: str
    tipo: str
    created_at: datetime
    updated_at: datetime
    indice_madurez: int | None = None  # de DiagnosticoTramite; None sin diagnóstico completo
    completado_en: datetime | None = None
    archivado_en: datetime | None = None

    model_config = {"from_attributes": True}


class VariableAdicionalOut(BaseModel):
    variable: str
    pregunta: str
    ayuda: str


class TipoTramiteOut(BaseModel):
    nombre: str
    etiqueta: str
    variables_excluidas: list[str]
    variables_adicionales: list[VariableAdicionalOut]


class PanelResumenOut(BaseModel):
    """Respuesta de GET /api/tramites. El promedio siempre viene de
    `app.dominio.madurez.calcular_indice_global`, nunca reimplementado acá."""

    tramites: list[TramiteOut]
    indice_global: float | None
    fecha_ultimo_diagnostico: datetime | None


class PuntoIndiceGlobalOut(BaseModel):
    """Un punto de la gráfica de tendencia -- dato real guardado por
    `enviar_diagnostico`, nunca simulado. `nivel_N_conteo`: distribución de
    trámites activos por nivel de madurez en ese instante."""

    indice_global: float
    nivel_0_conteo: int
    nivel_1_conteo: int
    nivel_2_conteo: int
    nivel_3_conteo: int
    nivel_4_conteo: int
    creado_en: datetime

    model_config = {"from_attributes": True}

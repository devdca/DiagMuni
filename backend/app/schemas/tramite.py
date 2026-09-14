from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.dominio.tipos_tramite_loader import cargar_tipos_tramite


class TramiteCreate(BaseModel):
    # QA (ronda 2, hallazgo #6): sin tope, la API aceptaba un nombre de 940
    # caracteres que rompía visualmente la tabla del panel -- sin riesgo de
    # seguridad (React ya escapa el texto), pero sin ningún límite razonable
    # tampoco. 150 es la fuente de verdad real; el frontend (PanelResumen.tsx)
    # pone el mismo tope solo para avisar al escribir, no al enviar.
    nombre: str = Field(min_length=1, max_length=150)
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
    # Tomados de DiagnosticoTramite (sin relación ORM declarada entre Tramite y
    # DiagnosticoTramite -- ver app/api/tramites.py) -- ausentes (None) mientras
    # el trámite no tenga un diagnóstico completo.
    indice_madurez: int | None = None
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
    """Respuesta de GET /api/tramites: la lista de trámites ya extendida arriba,
    más el agregado del panel resumen (docs/ux-brief.md, "2. Panel resumen") --
    el promedio SIEMPRE se calcula con app.dominio.madurez.calcular_indice_global,
    nunca reimplementado acá ni en el frontend."""

    tramites: list[TramiteOut]
    indice_global: float | None
    fecha_ultimo_diagnostico: datetime | None


class PuntoIndiceGlobalOut(BaseModel):
    """Un punto de la gráfica de tendencia del Panel de control (migración
    0015) -- dato real guardado por `enviar_diagnostico`, nunca simulado.
    `nivel_N_conteo` (migración 0016): distribución real de trámites activos
    por nivel de madurez en ese mismo instante, para la gráfica apilada."""

    indice_global: float
    nivel_0_conteo: int
    nivel_1_conteo: int
    nivel_2_conteo: int
    nivel_3_conteo: int
    nivel_4_conteo: int
    creado_en: datetime

    model_config = {"from_attributes": True}

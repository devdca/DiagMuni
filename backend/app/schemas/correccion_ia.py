from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RegistrarCorreccionRequest(BaseModel):
    """Ver app/aplicacion/bitacora_correcciones.py para el significado exacto de
    cada campo -- `pieza` identifica qué clasificador/generador produjo
    `salida_llm` (ej. "mecanismo_identidad")."""

    tramite_id: UUID | None = None
    pieza: str = Field(min_length=1, max_length=100)
    entrada_llm: str = Field(min_length=1, max_length=4000)
    salida_llm: str = Field(min_length=1, max_length=4000)
    correccion: str = Field(min_length=1, max_length=4000)
    ruta_llm: str | None = None


class CorreccionIaOut(BaseModel):
    id: UUID
    tramite_id: UUID | None
    pieza: str
    entrada_llm: str
    salida_llm: str
    correccion: str
    ruta_llm: str | None
    creado_por: UUID
    creado_en: datetime

    model_config = {"from_attributes": True}

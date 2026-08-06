from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator

# entregables/fase-2/variables-contexto-institucional.md, sección 2.6 -- mismo
# conjunto de 3 valores que el enum `conectividad_enum` de la migración 0003.
CONECTIVIDAD_VALORES_VALIDOS = frozenset({"estable", "intermitente", "sin_conexion"})


class ContextoInstitucionalIn(BaseModel):
    """Upsert parcial (sección 5.2 del documento de diseño) -- todos los campos
    opcionales, un PUT puede tocar un solo campo sin reenviar los demás. Los
    validadores debajo replican los mismos rangos que los CHECK de la migración
    0003, en español llano (mensaje bajo `ValueError`, FastAPI lo devuelve dentro
    del 422 estándar de Pydantic)."""

    poblacion_total: int | None = None
    personal_total_gobierno: int | None = None
    presupuesto_tic_anual: Decimal | None = None
    area_tic_existe: bool | None = None
    conectividad: str | None = None
    normativa_local_emitida: bool | None = None
    autoridad_gobernanza_digital: bool | None = None

    @field_validator("poblacion_total", "personal_total_gobierno")
    @classmethod
    def _entero_no_negativo(cls, valor: int | None) -> int | None:
        if valor is not None and valor < 0:
            raise ValueError("Este valor no puede ser negativo.")
        return valor

    @field_validator("presupuesto_tic_anual")
    @classmethod
    def _presupuesto_no_negativo(cls, valor: Decimal | None) -> Decimal | None:
        if valor is not None and valor < 0:
            raise ValueError("El presupuesto no puede ser un valor negativo.")
        return valor

    @field_validator("conectividad")
    @classmethod
    def _conectividad_valida(cls, valor: str | None) -> str | None:
        if valor is not None and valor not in CONECTIVIDAD_VALORES_VALIDOS:
            opciones = ", ".join(sorted(CONECTIVIDAD_VALORES_VALIDOS))
            raise ValueError(f"La conectividad debe ser una de estas opciones: {opciones}.")
        return valor


class ContextoInstitucionalOut(BaseModel):
    tenant_id: UUID
    poblacion_total: int | None
    personal_total_gobierno: int | None
    presupuesto_tic_anual: Decimal | None
    area_tic_existe: bool | None
    conectividad: str | None
    normativa_local_emitida: bool | None
    autoridad_gobernanza_digital: bool | None
    actualizado_en: datetime | None

    model_config = {"from_attributes": True}

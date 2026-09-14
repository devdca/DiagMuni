from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ValidationInfo, field_validator

# entregables/fase-2/variables-contexto-institucional.md, sección 2.6 -- mismo
# conjunto de valores que el enum `conectividad_enum` (migración 0003 + 0008).
CONECTIVIDAD_VALORES_VALIDOS = frozenset({"estable", "intermitente", "deficiente", "sin_conexion"})

# Migración 0008 (renombrado en 0010) -- mismo conjunto que el enum
# `infraestructura_firma_electronica_enum`.
INFRAESTRUCTURA_FIRMA_ELECTRONICA_VALORES_VALIDOS = frozenset({"propia", "proveedor_externo", "gobierno_estatal"})

# Migración 0009 -- un frozenset por cada enum de Postgres nuevo (mismos valores
# que backend/alembic/versions/0009_contexto_institucional_madurez_transversal.py).
_VALORES_VALIDOS_POR_CAMPO: dict[str, frozenset[str]] = {
    "portal_tramites_tipo": frozenset({"portal_unico", "paginas_independientes", "ninguno"}),
    "pagos_electronicos_generalizados": frozenset({"si", "no", "solo_algunos"}),
    "mecanismo_identidad_estandar": frozenset(
        {"llave_mx", "id_uruguay", "propio", "ninguno", "varia_por_tramite", "otro"}
    ),
    "interoperabilidad_entre_areas": frozenset({"si", "no", "parcialmente"}),
    "incidente_ciberseguridad_24meses": frozenset({"si", "no", "sin_registro"}),
    "rotacion_personal_ti": frozenset({"baja", "media", "alta", "no_se_mide"}),
    "dependencia_outsourcing_ti": frozenset({"si_totalmente", "si_parcialmente", "no"}),
    "accesibilidad_sistemas_discapacidad": frozenset({"si", "no", "parcialmente"}),
}


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
    agenda_simplificacion_publicada: bool | None = None
    portal_datos_abiertos_existe: bool | None = None
    linea_atencion_ciudadana_centralizada: bool | None = None
    capacitacion_personal_tic_anual: bool | None = None
    protocolo_ciberseguridad_existe: bool | None = None
    presupuesto_total_anual: Decimal | None = None
    numero_tramites_totales: int | None = None
    ingresos_propios_porcentaje: int | None = None
    numero_oficinas_atencion: int | None = None
    enlace_notificado_formalmente: bool | None = None
    convenio_colaboracion_estado: bool | None = None
    personal_area_ti: int | None = None
    infraestructura_firma_electronica: str | None = None
    porcentaje_tramites_en_linea: int | None = None
    porcentaje_tramites_en_linea_no_se_mide: bool | None = None
    portal_tramites_tipo: str | None = None
    pagos_electronicos_generalizados: str | None = None
    mecanismo_identidad_estandar: str | None = None
    interoperabilidad_entre_areas: str | None = None
    inventario_sistemas_existe: bool | None = None
    politica_gobierno_datos_existe: bool | None = None
    respaldos_periodicos_existen: bool | None = None
    incidente_ciberseguridad_24meses: str | None = None
    certificacion_seguridad_externa: bool | None = None
    rotacion_personal_ti: str | None = None
    dependencia_outsourcing_ti: str | None = None
    mide_tiempos_resolucion: bool | None = None
    mide_satisfaccion_ciudadana: bool | None = None
    tablero_indicadores_existe: bool | None = None
    fondos_digitalizacion_recibidos: bool | None = None
    fondos_digitalizacion_detalle: str | None = None
    porcentaje_poblacion_acceso_internet: int | None = None
    porcentaje_poblacion_acceso_internet_no_se_tiene_dato: bool | None = None
    accesibilidad_sistemas_discapacidad: str | None = None
    catalogo_tramites_propio_existe: bool | None = None

    @field_validator(
        "poblacion_total",
        "personal_total_gobierno",
        "numero_tramites_totales",
        "numero_oficinas_atencion",
        "personal_area_ti",
    )
    @classmethod
    def _entero_no_negativo(cls, valor: int | None) -> int | None:
        if valor is not None and valor < 0:
            raise ValueError("Este valor no puede ser negativo.")
        return valor

    @field_validator("presupuesto_tic_anual", "presupuesto_total_anual")
    @classmethod
    def _presupuesto_no_negativo(cls, valor: Decimal | None) -> Decimal | None:
        if valor is not None and valor < 0:
            raise ValueError("El presupuesto no puede ser un valor negativo.")
        return valor

    @field_validator(
        "ingresos_propios_porcentaje", "porcentaje_tramites_en_linea", "porcentaje_poblacion_acceso_internet"
    )
    @classmethod
    def _porcentaje_en_rango(cls, valor: int | None) -> int | None:
        if valor is not None and not (0 <= valor <= 100):
            raise ValueError("El porcentaje debe estar entre 0 y 100.")
        return valor

    @field_validator("conectividad")
    @classmethod
    def _conectividad_valida(cls, valor: str | None) -> str | None:
        if valor is not None and valor not in CONECTIVIDAD_VALORES_VALIDOS:
            opciones = ", ".join(sorted(CONECTIVIDAD_VALORES_VALIDOS))
            raise ValueError(f"La conectividad debe ser una de estas opciones: {opciones}.")
        return valor

    @field_validator("infraestructura_firma_electronica")
    @classmethod
    def _infraestructura_firma_electronica_valida(cls, valor: str | None) -> str | None:
        if valor is not None and valor not in INFRAESTRUCTURA_FIRMA_ELECTRONICA_VALORES_VALIDOS:
            opciones = ", ".join(sorted(INFRAESTRUCTURA_FIRMA_ELECTRONICA_VALORES_VALIDOS))
            raise ValueError(f"La infraestructura de firma electrónica debe ser una de estas opciones: {opciones}.")
        return valor

    @field_validator(*_VALORES_VALIDOS_POR_CAMPO.keys())
    @classmethod
    def _valor_de_enum_valido(cls, valor: str | None, info: ValidationInfo) -> str | None:
        nombre_campo = info.field_name
        assert nombre_campo is not None
        valores_validos = _VALORES_VALIDOS_POR_CAMPO[nombre_campo]
        if valor is not None and valor not in valores_validos:
            opciones = ", ".join(sorted(valores_validos))
            raise ValueError(f"{nombre_campo} debe ser una de estas opciones: {opciones}.")
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
    agenda_simplificacion_publicada: bool | None
    portal_datos_abiertos_existe: bool | None
    linea_atencion_ciudadana_centralizada: bool | None
    capacitacion_personal_tic_anual: bool | None
    protocolo_ciberseguridad_existe: bool | None
    presupuesto_total_anual: Decimal | None
    numero_tramites_totales: int | None
    ingresos_propios_porcentaje: int | None
    numero_oficinas_atencion: int | None
    enlace_notificado_formalmente: bool | None
    convenio_colaboracion_estado: bool | None
    personal_area_ti: int | None
    infraestructura_firma_electronica: str | None
    porcentaje_tramites_en_linea: int | None
    porcentaje_tramites_en_linea_no_se_mide: bool
    portal_tramites_tipo: str | None
    pagos_electronicos_generalizados: str | None
    mecanismo_identidad_estandar: str | None
    interoperabilidad_entre_areas: str | None
    inventario_sistemas_existe: bool | None
    politica_gobierno_datos_existe: bool | None
    respaldos_periodicos_existen: bool | None
    incidente_ciberseguridad_24meses: str | None
    certificacion_seguridad_externa: bool | None
    rotacion_personal_ti: str | None
    dependencia_outsourcing_ti: str | None
    mide_tiempos_resolucion: bool | None
    mide_satisfaccion_ciudadana: bool | None
    tablero_indicadores_existe: bool | None
    fondos_digitalizacion_recibidos: bool | None
    fondos_digitalizacion_detalle: str | None
    porcentaje_poblacion_acceso_internet: int | None
    porcentaje_poblacion_acceso_internet_no_se_tiene_dato: bool
    accesibilidad_sistemas_discapacidad: str | None
    catalogo_tramites_propio_existe: bool | None
    actualizado_en: datetime | None

    model_config = {"from_attributes": True}

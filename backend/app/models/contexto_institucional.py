import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ContextoInstitucional(Base):
    """Perfil de contexto y capacidad institucional del gobierno, 1:1 con tenant
    (entregables/fase-2/variables-contexto-institucional.md, sección 4). RLS por
    tenant_id igual que el resto de tablas de negocio -- ver
    backend/alembic/versions/0003_contexto_institucional.py. Todas las columnas de
    negocio son nullable y editables en cualquier momento, sin excepción."""

    __tablename__ = "contexto_institucional"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False, unique=True
    )
    poblacion_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    personal_total_gobierno: Mapped[int | None] = mapped_column(Integer, nullable=True)
    presupuesto_tic_anual: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    area_tic_existe: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    conectividad: Mapped[str | None] = mapped_column(
        Enum("estable", "intermitente", "deficiente", "sin_conexion", name="conectividad_enum"), nullable=True
    )
    normativa_local_emitida: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Única de las 7 variables de contexto/capacidad institucional original con
    # criterio_deteccion real en engine/reglas/ (ver
    # backend/app/engine/reglas/autoridad_gobernanza_digital.yaml).
    autoridad_gobernanza_digital: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # 5 variables agregadas (migración 0006) -- mismo patrón, cada una con su
    # propio criterio_deteccion real en engine/reglas/.
    agenda_simplificacion_publicada: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    portal_datos_abiertos_existe: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    linea_atencion_ciudadana_centralizada: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    capacitacion_personal_tic_anual: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    protocolo_ciberseguridad_existe: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # 4 variables agregadas (migración 0007) -- puramente informativas, no
    # generan brecha, solo alimentan el contexto de la capa de IA (ver
    # app/ia/contexto_gobierno.py).
    presupuesto_total_anual: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    numero_tramites_totales: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ingresos_propios_porcentaje: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero_oficinas_atencion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 4 variables agregadas (migración 0008) -- 2 con criterio_deteccion real en
    # engine/reglas/ (enlace_notificado_formalmente, convenio_colaboracion_estado)
    # y 2 puramente informativas.
    enlace_notificado_formalmente: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    convenio_colaboracion_estado: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    personal_area_ti: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Migración 0010: renombrado de infraestructura_fea (colisionaba con "fea").
    infraestructura_firma_electronica: Mapped[str | None] = mapped_column(
        Enum("propia", "proveedor_externo", "gobierno_estatal", name="infraestructura_firma_electronica_enum"),
        nullable=True,
    )
    # 19 variables agregadas (migración 0009) -- madurez digital transversal,
    # interoperabilidad, ciberseguridad, capital humano de TI, medición,
    # financiamiento y accesibilidad. Todas puramente informativas (ver
    # app/ia/contexto_gobierno.py) -- ninguna tiene criterio_deteccion propio.
    porcentaje_tramites_en_linea: Mapped[int | None] = mapped_column(Integer, nullable=True)
    porcentaje_tramites_en_linea_no_se_mide: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    portal_tramites_tipo: Mapped[str | None] = mapped_column(
        Enum("portal_unico", "paginas_independientes", "ninguno", name="portal_tramites_tipo_enum"), nullable=True
    )
    pagos_electronicos_generalizados: Mapped[str | None] = mapped_column(
        Enum("si", "no", "solo_algunos", name="pagos_electronicos_generalizados_enum"), nullable=True
    )
    mecanismo_identidad_estandar: Mapped[str | None] = mapped_column(
        Enum(
            "llave_mx",
            "id_uruguay",
            "propio",
            "ninguno",
            "varia_por_tramite",
            "otro",
            name="mecanismo_identidad_estandar_enum",
        ),
        nullable=True,
    )
    interoperabilidad_entre_areas: Mapped[str | None] = mapped_column(
        Enum("si", "no", "parcialmente", name="interoperabilidad_entre_areas_enum"), nullable=True
    )
    inventario_sistemas_existe: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    politica_gobierno_datos_existe: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    respaldos_periodicos_existen: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    incidente_ciberseguridad_24meses: Mapped[str | None] = mapped_column(
        Enum("si", "no", "sin_registro", name="incidente_ciberseguridad_24meses_enum"), nullable=True
    )
    certificacion_seguridad_externa: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    rotacion_personal_ti: Mapped[str | None] = mapped_column(
        Enum("baja", "media", "alta", "no_se_mide", name="rotacion_personal_ti_enum"), nullable=True
    )
    dependencia_outsourcing_ti: Mapped[str | None] = mapped_column(
        Enum("si_totalmente", "si_parcialmente", "no", name="dependencia_outsourcing_ti_enum"), nullable=True
    )
    mide_tiempos_resolucion: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    mide_satisfaccion_ciudadana: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    tablero_indicadores_existe: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fondos_digitalizacion_recibidos: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fondos_digitalizacion_detalle: Mapped[str | None] = mapped_column(String, nullable=True)
    porcentaje_poblacion_acceso_internet: Mapped[int | None] = mapped_column(Integer, nullable=True)
    porcentaje_poblacion_acceso_internet_no_se_tiene_dato: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    accesibilidad_sistemas_discapacidad: Mapped[str | None] = mapped_column(
        Enum("si", "no", "parcialmente", name="accesibilidad_sistemas_discapacidad_enum"), nullable=True
    )
    catalogo_tramites_propio_existe: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    actualizado_en: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

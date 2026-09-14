"""contexto_institucional: 19 variables nuevas de madurez digital transversal,
interoperabilidad, ciberseguridad, capital humano de TI, medición, financiamiento
y accesibilidad -- todas puramente informativas (alimentan app/ia/contexto_gobierno.py,
ninguna tiene criterio_deteccion en engine/reglas/). 2 de ellas (porcentaje de
trámites en línea y porcentaje de población con acceso a internet) van acompañadas
de un booleano hermano "no_se_mide"/"no_se_tiene_dato" -- null en el campo numérico
sigue significando "sin llenar", el booleano es la respuesta explícita de que el
gobierno no lleva ese dato.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-08

"""

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

_ENUMS: dict[str, tuple[str, ...]] = {
    "portal_tramites_tipo_enum": ("portal_unico", "paginas_independientes", "ninguno"),
    "pagos_electronicos_generalizados_enum": ("si", "no", "solo_algunos"),
    "mecanismo_identidad_estandar_enum": (
        "llave_mx",
        "id_uruguay",
        "propio",
        "ninguno",
        "varia_por_tramite",
        "otro",
    ),
    "interoperabilidad_entre_areas_enum": ("si", "no", "parcialmente"),
    "incidente_ciberseguridad_24meses_enum": ("si", "no", "sin_registro"),
    "rotacion_personal_ti_enum": ("baja", "media", "alta", "no_se_mide"),
    "dependencia_outsourcing_ti_enum": ("si_totalmente", "si_parcialmente", "no"),
    "accesibilidad_sistemas_discapacidad_enum": ("si", "no", "parcialmente"),
}

_BOOLEANOS = (
    "inventario_sistemas_existe",
    "politica_gobierno_datos_existe",
    "respaldos_periodicos_existen",
    "certificacion_seguridad_externa",
    "mide_tiempos_resolucion",
    "mide_satisfaccion_ciudadana",
    "tablero_indicadores_existe",
    "fondos_digitalizacion_recibidos",
    "catalogo_tramites_propio_existe",
)


def upgrade() -> None:
    op.add_column(
        "contexto_institucional", sa.Column("porcentaje_tramites_en_linea", sa.Integer(), nullable=True)
    )
    op.add_column(
        "contexto_institucional",
        sa.Column(
            "porcentaje_tramites_en_linea_no_se_mide", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "contexto_institucional", sa.Column("porcentaje_poblacion_acceso_internet", sa.Integer(), nullable=True)
    )
    op.add_column(
        "contexto_institucional",
        sa.Column(
            "porcentaje_poblacion_acceso_internet_no_se_tiene_dato",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    for columna in _BOOLEANOS:
        op.add_column("contexto_institucional", sa.Column(columna, sa.Boolean(), nullable=True))

    op.add_column("contexto_institucional", sa.Column("fondos_digitalizacion_detalle", sa.String(), nullable=True))

    for nombre_enum, valores in _ENUMS.items():
        enum_pg = sa.Enum(*valores, name=nombre_enum)
        enum_pg.create(op.get_bind(), checkfirst=True)
        columna = nombre_enum.removesuffix("_enum")
        op.add_column("contexto_institucional", sa.Column(columna, enum_pg, nullable=True))

    op.create_check_constraint(
        "ck_contexto_institucional_porcentaje_tramites_en_linea_rango",
        "contexto_institucional",
        "porcentaje_tramites_en_linea IS NULL OR porcentaje_tramites_en_linea BETWEEN 0 AND 100",
    )
    op.create_check_constraint(
        "ck_contexto_institucional_porcentaje_poblacion_internet_rango",
        "contexto_institucional",
        "porcentaje_poblacion_acceso_internet IS NULL OR porcentaje_poblacion_acceso_internet BETWEEN 0 AND 100",
    )


def downgrade() -> None:
    op.drop_constraint("ck_contexto_institucional_porcentaje_poblacion_internet_rango", "contexto_institucional")
    op.drop_constraint("ck_contexto_institucional_porcentaje_tramites_en_linea_rango", "contexto_institucional")

    for nombre_enum in _ENUMS:
        columna = nombre_enum.removesuffix("_enum")
        op.drop_column("contexto_institucional", columna)
        op.execute(f"DROP TYPE {nombre_enum}")

    op.drop_column("contexto_institucional", "fondos_digitalizacion_detalle")
    for columna in reversed(_BOOLEANOS):
        op.drop_column("contexto_institucional", columna)

    op.drop_column("contexto_institucional", "porcentaje_poblacion_acceso_internet_no_se_tiene_dato")
    op.drop_column("contexto_institucional", "porcentaje_poblacion_acceso_internet")
    op.drop_column("contexto_institucional", "porcentaje_tramites_en_linea_no_se_mide")
    op.drop_column("contexto_institucional", "porcentaje_tramites_en_linea")

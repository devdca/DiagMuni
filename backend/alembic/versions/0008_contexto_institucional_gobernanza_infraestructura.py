"""contexto_institucional: 4 variables nuevas -- 2 con criterio_deteccion real
(enlace_notificado_formalmente, convenio_colaboracion_estado, ver app/engine/
reglas/) y 2 puramente informativas (personal_area_ti, infraestructura_fea).
También agrega "deficiente" al enum conectividad_enum (entre intermitente y
sin_conexion).

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-07

"""

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE conectividad_enum ADD VALUE IF NOT EXISTS 'deficiente' BEFORE 'sin_conexion'")

    op.add_column("contexto_institucional", sa.Column("enlace_notificado_formalmente", sa.Boolean(), nullable=True))
    op.add_column("contexto_institucional", sa.Column("convenio_colaboracion_estado", sa.Boolean(), nullable=True))
    op.add_column("contexto_institucional", sa.Column("personal_area_ti", sa.Integer(), nullable=True))

    infraestructura_fea_enum = sa.Enum(
        "propia", "proveedor_externo", "gobierno_estatal", name="infraestructura_fea_enum"
    )
    infraestructura_fea_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "contexto_institucional", sa.Column("infraestructura_fea", infraestructura_fea_enum, nullable=True)
    )

    op.create_check_constraint(
        "ck_contexto_institucional_personal_area_ti_no_negativo",
        "contexto_institucional",
        "personal_area_ti IS NULL OR personal_area_ti >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_contexto_institucional_personal_area_ti_no_negativo", "contexto_institucional")

    op.drop_column("contexto_institucional", "infraestructura_fea")
    op.drop_column("contexto_institucional", "personal_area_ti")
    op.drop_column("contexto_institucional", "convenio_colaboracion_estado")
    op.drop_column("contexto_institucional", "enlace_notificado_formalmente")

    op.execute("DROP TYPE infraestructura_fea_enum")

    # Postgres no soporta quitar un valor de un enum -- el downgrade deja
    # "deficiente" presente pero inutilizado, mismo criterio que cualquier
    # ADD VALUE de enum en Postgres (operación no reversible de forma nativa).

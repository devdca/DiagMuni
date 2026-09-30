"""Renombra `infraestructura_fea` -> `infraestructura_firma_electronica` (y su
enum) -- el nombre corto colisionaba con la palabra "fea" en español. No se edita
la migración 0008 original (ya aplicada) -- un rename es la vía correcta para una
columna que ya existe en bases reales.

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-08

"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "contexto_institucional", "infraestructura_fea", new_column_name="infraestructura_firma_electronica"
    )
    op.execute("ALTER TYPE infraestructura_fea_enum RENAME TO infraestructura_firma_electronica_enum")


def downgrade() -> None:
    op.execute("ALTER TYPE infraestructura_firma_electronica_enum RENAME TO infraestructura_fea_enum")
    op.alter_column(
        "contexto_institucional", "infraestructura_firma_electronica", new_column_name="infraestructura_fea"
    )

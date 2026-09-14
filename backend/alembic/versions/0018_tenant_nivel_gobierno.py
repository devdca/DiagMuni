"""tenant: nivel_gobierno (municipal/estatal/federal) -- primer paso de la
expansión de DiagMuni a los tres órdenes de gobierno (Fase A). Ortogonal a
`pais`: un mismo país puede tener tenants municipales, estatales y federales.

CHECK constraint, no Enum nativo de Postgres -- mismo motivo que
`proveedor_llm_preferido` (migración 0016): agregar un cuarto nivel más
adelante es un ALTER TABLE normal, sin la restricción de ALTER TYPE ADD VALUE.

`server_default="municipal"`: todo tenant existente hoy es municipal (es lo
único que el producto modelaba hasta ahora), así que la migración no
requiere backfill manual y es retrocompatible sin downtime.

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-10

"""

import sqlalchemy as sa

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

_NIVELES_VALIDOS = ("municipal", "estatal", "federal")


def upgrade() -> None:
    op.add_column(
        "tenant",
        sa.Column("nivel_gobierno", sa.String(), nullable=False, server_default="municipal"),
    )
    op.create_check_constraint(
        "ck_tenant_nivel_gobierno_valido",
        "tenant",
        "nivel_gobierno IN " f"({', '.join(repr(n) for n in _NIVELES_VALIDOS)})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tenant_nivel_gobierno_valido", "tenant")
    op.drop_column("tenant", "nivel_gobierno")

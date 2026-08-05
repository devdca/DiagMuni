"""tenant.clave: identificador corto y legible para resolver el gobierno en el login
(entregables/fase-2/identificacion-gobierno-login.md, secciones 1-2)

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-04

"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable primero: agregar NOT NULL directo rompería con filas ya existentes
    # del piloto (entregables/fase-2/identificacion-gobierno-login.md, sección 2).
    op.add_column("tenant", sa.Column("clave", sa.String(), nullable=True))

    # Backfill de filas ya sembradas: deriva una clave provisional a partir de
    # `nombre` (trim + minúsculas + no alfanumérico -> guion). Una colisión entre
    # dos tenants ya existentes es corrección manual de datos, no algo que esta
    # migración deba resolver con sufijos automáticos.
    op.execute(
        "UPDATE tenant SET clave = lower(regexp_replace(regexp_replace(trim(nombre), "
        "'[^a-zA-Z0-9]+', '-', 'g'), '-+$', '')) WHERE clave IS NULL;"
    )

    op.alter_column("tenant", "clave", nullable=False)
    op.create_unique_constraint("uq_tenant_clave", "tenant", ["clave"])


def downgrade() -> None:
    op.drop_constraint("uq_tenant_clave", "tenant")
    op.drop_column("tenant", "clave")

"""nota_seguimiento: notas colaborativas sobre una acción de seguimiento (F6
ampliado) -- comentarios con autor y fecha, para coordinarse dentro del producto
en vez de por fuera de él.

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-08

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nota_seguimiento",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column(
            "accion_seguimiento_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accion_seguimiento.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("texto", sa.String(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_nota_seguimiento_tenant_id", "nota_seguimiento", ["tenant_id"])
    op.create_index("ix_nota_seguimiento_accion_seguimiento_id", "nota_seguimiento", ["accion_seguimiento_id"])

    op.execute("ALTER TABLE nota_seguimiento ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE nota_seguimiento FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON nota_seguimiento
          USING (tenant_id = current_setting('app.tenant_id')::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON nota_seguimiento")
    op.drop_table("nota_seguimiento")

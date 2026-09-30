"""contexto_institucional: 4 variables nuevas puramente informativas (no generan
brecha, solo alimentan el contexto que se le manda a la capa de IA -- ver
app/ia/contexto_gobierno.py) -- presupuesto total, número de trámites totales,
% de ingresos propios, número de oficinas de atención.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-07

"""

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contexto_institucional", sa.Column("presupuesto_total_anual", sa.Numeric(16, 2), nullable=True))
    op.add_column("contexto_institucional", sa.Column("numero_tramites_totales", sa.Integer(), nullable=True))
    op.add_column("contexto_institucional", sa.Column("ingresos_propios_porcentaje", sa.Integer(), nullable=True))
    op.add_column("contexto_institucional", sa.Column("numero_oficinas_atencion", sa.Integer(), nullable=True))

    op.create_check_constraint(
        "ck_contexto_institucional_presupuesto_total_no_negativo",
        "contexto_institucional",
        "presupuesto_total_anual IS NULL OR presupuesto_total_anual >= 0",
    )
    op.create_check_constraint(
        "ck_contexto_institucional_numero_tramites_no_negativo",
        "contexto_institucional",
        "numero_tramites_totales IS NULL OR numero_tramites_totales >= 0",
    )
    op.create_check_constraint(
        "ck_contexto_institucional_ingresos_propios_rango",
        "contexto_institucional",
        "ingresos_propios_porcentaje IS NULL OR ingresos_propios_porcentaje BETWEEN 0 AND 100",
    )
    op.create_check_constraint(
        "ck_contexto_institucional_numero_oficinas_no_negativo",
        "contexto_institucional",
        "numero_oficinas_atencion IS NULL OR numero_oficinas_atencion >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_contexto_institucional_numero_oficinas_no_negativo", "contexto_institucional")
    op.drop_constraint("ck_contexto_institucional_ingresos_propios_rango", "contexto_institucional")
    op.drop_constraint("ck_contexto_institucional_numero_tramites_no_negativo", "contexto_institucional")
    op.drop_constraint("ck_contexto_institucional_presupuesto_total_no_negativo", "contexto_institucional")

    op.drop_column("contexto_institucional", "numero_oficinas_atencion")
    op.drop_column("contexto_institucional", "ingresos_propios_porcentaje")
    op.drop_column("contexto_institucional", "numero_tramites_totales")
    op.drop_column("contexto_institucional", "presupuesto_total_anual")

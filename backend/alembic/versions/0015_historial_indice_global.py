"""historial_indice_global: un punto por cada vez que se envía/corrige un
diagnóstico (app/adaptadores/http/diagnosticos.py::enviar_diagnostico), con el
índice global del tenant recalculado en ese instante (misma fórmula que el
panel resumen, app/dominio/madurez.py::calcular_indice_global). Alimenta la
gráfica real de tendencia del Panel de control -- antes de esta migración no
existía ningún historial persistido del índice global, solo el valor
instantáneo que GET /api/tramites recalcula cada vez; docs/ux-brief.md decía
"sin gráficas de tendencia en el MVP" justamente porque no había con qué
graficar todavía.

Mismo patrón de aislamiento que evento_historial (migración 0012): RLS forzado
por tenant_id, tabla append-only (nunca se actualiza ni se borra un punto ya
escrito).

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-09

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "historial_indice_global",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("indice_global", sa.Float(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_historial_indice_global_tenant_id", "historial_indice_global", ["tenant_id"])
    # Compuesto: la lectura para la gráfica siempre filtra por tenant Y ordena
    # por fecha (app/aplicacion/historial_indice_global.py::listar_historial_indice_global).
    op.create_index(
        "ix_historial_indice_global_tenant_creado", "historial_indice_global", ["tenant_id", "creado_en"]
    )

    op.execute("ALTER TABLE historial_indice_global ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE historial_indice_global FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON historial_indice_global
          USING (tenant_id = current_setting('app.tenant_id')::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON historial_indice_global")
    op.drop_table("historial_indice_global")

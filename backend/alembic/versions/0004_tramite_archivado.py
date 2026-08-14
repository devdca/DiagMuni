"""tramite.archivado_en: archivado reversible de un trámite ya diagnosticado,
sin borrar ninguna fila (docs/plan-implementacion-alta-gobierno.md no cubre esto;
diseño en docs/app-flow.md, "Casos especiales" -- eliminar/archivar un trámite).

`NULL` = no archivado (default). Solo se registra CUÁNDO se archivó -- ortogonal
a `estado` (la máquina de estados de docs/app-flow.md sigue avanzando igual;
archivar/desarchivar no la toca).

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-14

"""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tramite", sa.Column("archivado_en", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("tramite", "archivado_en")

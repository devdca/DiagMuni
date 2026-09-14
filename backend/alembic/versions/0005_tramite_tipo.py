"""tramite.tipo: qué tipo de trámite es (catálogo en app/engine/tipos_tramite.yaml,
nunca un Enum de Postgres -- agregar un tipo nuevo no debe requerir migración).

Decide qué preguntas del cuestionario se muestran (app/engine/tipos_tramite_loader.py).
`server_default='generico'` es solo para no romper filas existentes al agregar la
columna -- "generico" es el mismo comportamiento de siempre (las 6 preguntas).

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-07

"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tramite",
        sa.Column("tipo", sa.String(), nullable=False, server_default="generico"),
    )


def downgrade() -> None:
    op.drop_column("tramite", "tipo")

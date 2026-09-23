"""contexto_institucional: 5 variables nuevas de capacidad institucional -- agenda de
simplificación (LNETB), portal de datos abiertos, línea de atención ciudadana,
capacitación digital del personal, protocolo de ciberseguridad. Mismo patrón que
`autoridad_gobernanza_digital` (migración 0003): nullable, editable en cualquier
momento, con criterio_deteccion real en app/engine/reglas/.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-07

"""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_COLUMNAS = (
    "agenda_simplificacion_publicada",
    "portal_datos_abiertos_existe",
    "linea_atencion_ciudadana_centralizada",
    "capacitacion_personal_tic_anual",
    "protocolo_ciberseguridad_existe",
)


def upgrade() -> None:
    for columna in _COLUMNAS:
        op.add_column("contexto_institucional", sa.Column(columna, sa.Boolean(), nullable=True))


def downgrade() -> None:
    for columna in _COLUMNAS:
        op.drop_column("contexto_institucional", columna)

"""Extiende historial_indice_global con el conteo de trámites activos en cada
nivel de madurez (0-4) al momento del snapshot -- misma fila, mismo evento
(enviar_diagnostico), no una tabla aparte: ambos números (promedio global y
distribución por nivel) se calculan del mismo `indices` en el mismo instante,
así que viven juntos.

Alimenta la gráfica de tendencia apilada del Panel de control (pedido
explícito: que se vea como un "gradient stacked area chart", pero con datos
reales -- cuántos trámites hay en cada nivel de la rampa, no series
inventadas). Reutiliza los 5 colores de la rampa ya validada
(frontend/src/lib/madurez.ts), cero paleta nueva.

Filas existentes (previas a esta migración) quedan en 0/0/0/0/0 -- son datos
de prueba de antes de esta funcionalidad, no hay manera de reconstruir
retroactivamente cuántos trámites había en cada nivel en ese momento.

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-09

"""

import sqlalchemy as sa

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

NIVELES = (0, 1, 2, 3, 4)


def upgrade() -> None:
    for nivel in NIVELES:
        op.add_column(
            "historial_indice_global",
            sa.Column(f"nivel_{nivel}_conteo", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    for nivel in NIVELES:
        op.drop_column("historial_indice_global", f"nivel_{nivel}_conteo")

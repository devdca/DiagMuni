"""RBAC mínimo (docs/backend-schema.md, "Riesgos abiertos" #1, ya no abierto):
agrega el rol `admin_gobierno` al enum existente (`funcionario` sigue siendo el
default) y dos columnas de gestión de cuenta que el panel de administración
necesita -- `activo` (alta/baja reversible de un funcionario, hoy imposible sin
tocar la base de datos a mano) y `ultimo_login_en` (visibilidad de cuentas
inactivas de verdad, no solo desactivadas).

`ALTER TYPE ... ADD VALUE` corre en su propia migración, sin usar el valor nuevo
en ningún INSERT/UPDATE de este mismo archivo -- Postgres 12+ no permite ambas
cosas en la misma transacción, y cada migración de Alembic corre en la suya.

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-08

"""

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE rol_enum ADD VALUE IF NOT EXISTS 'admin_gobierno'")
    op.add_column(
        "usuario", sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true())
    )
    op.add_column("usuario", sa.Column("ultimo_login_en", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("usuario", "ultimo_login_en")
    op.drop_column("usuario", "activo")
    # Postgres no permite quitar un valor de un enum sin recrear el tipo -- fuera
    # de alcance de este downgrade (ningún downgrade existente en el proyecto
    # revierte un ADD VALUE de enum; un `admin_gobierno` ya asignado bloquearía
    # el DROP TYPE de todas formas).

"""contexto_institucional: perfil de contexto y capacidad institucional del gobierno,
1:1 con tenant (entregables/fase-2/variables-contexto-institucional.md, sección 4)

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-05

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conectividad_enum = postgresql.ENUM(
        "estable", "intermitente", "sin_conexion", name="conectividad_enum"
    )

    op.create_table(
        "contexto_institucional",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False
        ),
        sa.Column("poblacion_total", sa.Integer(), nullable=True),
        sa.Column("personal_total_gobierno", sa.Integer(), nullable=True),
        sa.Column("presupuesto_tic_anual", sa.Numeric(14, 2), nullable=True),
        sa.Column("area_tic_existe", sa.Boolean(), nullable=True),
        sa.Column("conectividad", conectividad_enum, nullable=True),
        sa.Column("normativa_local_emitida", sa.Boolean(), nullable=True),
        sa.Column("autoridad_gobernanza_digital", sa.Boolean(), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        "uq_contexto_institucional_tenant", "contexto_institucional", ["tenant_id"]
    )
    op.create_check_constraint(
        "ck_contexto_institucional_poblacion_no_negativa",
        "contexto_institucional",
        "poblacion_total IS NULL OR poblacion_total >= 0",
    )
    op.create_check_constraint(
        "ck_contexto_institucional_personal_no_negativo",
        "contexto_institucional",
        "personal_total_gobierno IS NULL OR personal_total_gobierno >= 0",
    )
    op.create_check_constraint(
        "ck_contexto_institucional_presupuesto_no_negativo",
        "contexto_institucional",
        "presupuesto_tic_anual IS NULL OR presupuesto_tic_anual >= 0",
    )

    # RLS -- mismo patrón real que backend/alembic/versions/0001_initial_schema.py
    # líneas 156-168 (ENABLE -> FORCE -> CREATE POLICY). FORCE es necesario porque
    # el usuario de la app es el mismo que corre la migración (dueño de la tabla),
    # y por default Postgres exime al dueño de RLS.
    op.execute("ALTER TABLE contexto_institucional ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE contexto_institucional FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON contexto_institucional
          USING (tenant_id = current_setting('app.tenant_id')::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON contexto_institucional")
    op.drop_constraint("ck_contexto_institucional_presupuesto_no_negativo", "contexto_institucional")
    op.drop_constraint("ck_contexto_institucional_personal_no_negativo", "contexto_institucional")
    op.drop_constraint("ck_contexto_institucional_poblacion_no_negativa", "contexto_institucional")
    op.drop_constraint("uq_contexto_institucional_tenant", "contexto_institucional")
    op.drop_table("contexto_institucional")
    # A diferencia de `upgrade()` (donde `create_table` ya crea el tipo por su cuenta
    # vía el evento automático de SQLAlchemy -- crearlo también a mano ahí duplica la
    # llamada y revienta con "already exists"), `drop_table` no borra el tipo con
    # nombre por su cuenta: sin este drop explícito, el tipo queda huérfano y una
    # siguiente corrida de `upgrade()` revienta igual, ahora por el lado contrario.
    postgresql.ENUM(name="conectividad_enum").drop(op.get_bind())

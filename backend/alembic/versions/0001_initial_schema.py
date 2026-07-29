"""esquema inicial: 7 tablas + RLS (docs/backend-schema.md)

Revision ID: 0001
Revises:
Create Date: 2026-07-28

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Tablas con tenant_id, todas reciben la misma policy RLS (docs/backend-schema.md, "Políticas RLS").
TABLAS_CON_RLS = (
    "usuario",
    "tramite",
    "diagnostico_tramite",
    "plan_modernizacion",
    "accion_seguimiento",
    "job",
)


def upgrade() -> None:
    op.create_table(
        "tenant",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("pais", sa.Enum("mx", "uy", name="pais_enum"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "usuario",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("rol", sa.Enum("funcionario", name="rol_enum"), nullable=False, server_default="funcionario"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "email", name="uq_usuario_tenant_email"),
    )
    op.create_index("ix_usuario_tenant_id", "usuario", ["tenant_id"])

    op.create_table(
        "tramite",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=False, server_default=""),
        sa.Column(
            "estado",
            sa.Enum(
                "sin_iniciar",
                "en_progreso",
                "diagnosticado",
                "generando_plan",
                "plan_listo",
                name="estado_tramite_enum",
            ),
            nullable=False,
            server_default="sin_iniciar",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "nombre", name="uq_tramite_tenant_nombre"),
    )
    op.create_index("ix_tramite_tenant_id", "tramite", ["tenant_id"])

    op.create_table(
        "diagnostico_tramite",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tramite_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tramite.id"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("respuestas", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("indice_madurez", sa.SmallInteger(), nullable=True),
        sa.Column("version_motor", sa.String(), nullable=True),
        sa.Column("completado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_diagnostico_tramite_tenant_id", "diagnostico_tramite", ["tenant_id"])

    op.create_table(
        "plan_modernizacion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "diagnostico_tramite_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("diagnostico_tramite.id"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("modo", sa.Enum("llm", "degradado", name="modo_plan_enum"), nullable=False),
        sa.Column("contenido", postgresql.JSONB(), nullable=False),
        sa.Column("verificado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("generado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_plan_modernizacion_tenant_id", "plan_modernizacion", ["tenant_id"])

    op.create_table(
        "accion_seguimiento",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "plan_modernizacion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("plan_modernizacion.id"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=False),
        sa.Column("responsable", sa.String(), nullable=False),
        sa.Column("fecha_objetivo", sa.Date(), nullable=False),
        sa.Column(
            "estado_semaforo",
            sa.Enum("completado", "en_progreso", "atrasado", name="estado_semaforo_enum"),
            nullable=False,
            server_default="en_progreso",
        ),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_accion_seguimiento_tenant_id", "accion_seguimiento", ["tenant_id"])

    op.create_table(
        "job",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("tipo", sa.Enum("generacion_plan", name="tipo_job_enum"), nullable=False),
        sa.Column(
            "diagnostico_tramite_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("diagnostico_tramite.id"),
            nullable=True,
        ),
        sa.Column(
            "estado",
            sa.Enum("pending", "running", "done", "failed", name="estado_job_enum"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("intentos", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("resultado", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_job_tenant_id", "job", ["tenant_id"])

    # RLS (docs/backend-schema.md, "Políticas RLS") — misma policy en las 6 tablas con tenant_id.
    # FORCE (no solo ENABLE) es necesario: por default Postgres exime al dueño de la tabla de RLS,
    # y en este docker-compose el usuario de la app es el mismo que corrió la migración (el dueño).
    # Sin FORCE, la policy sería "la única barrera" solo de nombre — la app la saltaría en silencio.
    for tabla in TABLAS_CON_RLS:
        op.execute(f"ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tabla} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {tabla}
              USING (tenant_id = current_setting('app.tenant_id')::uuid)
            """
        )


def downgrade() -> None:
    for tabla in TABLAS_CON_RLS:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {tabla}")
    op.drop_table("job")
    op.drop_table("accion_seguimiento")
    op.drop_table("plan_modernizacion")
    op.drop_table("diagnostico_tramite")
    op.drop_table("tramite")
    op.drop_table("usuario")
    op.drop_table("tenant")

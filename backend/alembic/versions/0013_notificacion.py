"""notificacion: centro de notificaciones (campana de la barra superior) --
avisos tenant-wide (sin destinatario individual ni estado de lectura por
usuario en esta primera versión: cualquier funcionario del gobierno ve y puede
marcar como leída la misma notificación, mismo criterio de simplicidad que
`accion_seguimiento.estado_semaforo`, que tampoco distingue quién lo actualizó).

`tipo` es texto libre, igual que `evento_historial.tipo` -- ver esa migración.

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-08

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notificacion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False),
        # ondelete="CASCADE" -- mismo motivo que evento_historial.tramite_id
        # (migración 0012): `eliminar_tramite` permite borrado físico de un
        # trámite archivado, y una notificación sobre un trámite que ya no
        # existe no tiene valor.
        sa.Column(
            "tramite_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tramite.id", ondelete="CASCADE"),
            nullable=True,
        ),
        # Solo se llena para tipo="accion_atrasada" -- permite no duplicar una
        # notificación por la misma acción cada vez que se revisa (ver
        # app/aplicacion/notificaciones.py::generar_notificaciones_acciones_atrasadas,
        # que no corre en un cron: se revisa perezosamente al listar, mismo patrón
        # sin scheduler que `revisar_job_obsoleto` en app/aplicacion/plan_job.py).
        sa.Column(
            "accion_seguimiento_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accion_seguimiento.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("titulo", sa.String(), nullable=False),
        sa.Column("mensaje", sa.String(), nullable=False),
        sa.Column("leida", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notificacion_tenant_id", "notificacion", ["tenant_id"])

    op.execute("ALTER TABLE notificacion ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE notificacion FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON notificacion
          USING (tenant_id = current_setting('app.tenant_id')::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON notificacion")
    op.drop_table("notificacion")

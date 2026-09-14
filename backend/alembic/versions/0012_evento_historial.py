"""evento_historial: bitácora persistida por trámite (pantalla "Historial" -- línea
de tiempo de diagnósticos, planes y acciones de un trámite). Hasta ahora
`app/core/audit_log.py` solo mandaba estos eventos a stdout; esta tabla los deja
consultables desde el propio producto (F8, trazabilidad normativa), sin
reemplazar el log de stdout (append-only, mismo criterio de ese módulo).

`tipo` es texto libre, no un enum de Postgres a propósito: la lista de tipos de
evento puede crecer sin requerir una migración nueva cada vez (validado en
`app/aplicacion/historial.py`, capa de aplicación, no en el esquema).

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-08

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evento_historial",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False),
        # ondelete="CASCADE": `eliminar_tramite` (app/adaptadores/http/tramites.py)
        # permite el borrado físico de un trámite archivado sin diagnóstico enviado
        # -- si ya tiene eventos de historial (ej. "archivado"), sin CASCADE el
        # DELETE de `tramite` reventaría con una FK violation. Un evento de
        # historial de un trámite que ya no existe no tiene ningún valor.
        sa.Column("tramite_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tramite.id", ondelete="CASCADE"), nullable=False),
        # Sin FK a `usuario` a propósito: varios flujos de prueba/servicio operan
        # con un `usuario_id` de claim que no siempre corresponde a una fila real
        # (ej. tokens de prueba contra Postgres real, ver tests de esta app) --
        # es un campo de atribución para mostrar en la UI, no una relación que deba
        # bloquear el insert del evento si no resuelve. Ningún flujo real borra
        # usuarios (solo los desactiva, migración 0011), así que tampoco hay riesgo
        # de huérfanos por ese lado.
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=False),
        sa.Column("metadatos", postgresql.JSONB(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_evento_historial_tenant_id", "evento_historial", ["tenant_id"])
    op.create_index("ix_evento_historial_tramite_id", "evento_historial", ["tramite_id"])

    op.execute("ALTER TABLE evento_historial ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE evento_historial FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON evento_historial
          USING (tenant_id = current_setting('app.tenant_id')::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON evento_historial")
    op.drop_table("evento_historial")

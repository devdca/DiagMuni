"""correccion_ia: bitácora de correcciones humanas sobre salidas de la capa de
IA -- pieza 3 de la nota de arquitectura "De Municipio a Tres Órdenes" (RAG +
bitácora + factibilidad, nunca "reentrenar el modelo").

Cada fila es un evento append-only (mismo criterio que `evento_historial`,
migración 0012): nunca se edita ni se borra una corrección ya guardada. Un
humano corrigiendo/rechazando una salida de IA es exactamente el dato que
sirve para (a) few-shot real en el prompt de la próxima clasificación
parecida, y (b) un conjunto de evaluación para medir si un cambio de
prompt/modelo mejora o empeora contra errores ya conocidos -- ninguno de los
dos usos requiere reentrenar nada, solo consultar esta tabla en el momento de
generar (RAG) o antes de promover un cambio a producción (evaluación).

`tramite_id` nullable: casi toda corrección hoy nace de F1 (asistente de
captura), atada a un trámite -- pero el diseño no debe asumir que siempre
habrá uno (una corrección futura sobre una narrativa de plan sin trámite
específico, o sobre una regla general, sigue siendo una corrección válida).

`ruta_llm` nullable: los endpoints de clasificación actuales
(app/adaptadores/http/asistente_captura.py) no devuelven todavía qué ruta
(economico/calidad/...) resolvió la llamada -- ver TODO en
app/aplicacion/bitacora_correcciones.py. Se deja el campo listo para cuando
se agregue esa información, en vez de forzar un valor falso ahora.

RLS por tenant_id, mismo patrón que nota_seguimiento (migración 0014).

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-10

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "correccion_ia",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("tramite_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tramite.id", ondelete="CASCADE")),
        # Qué pieza de la capa de IA generó la salida corregida -- valor libre a
        # propósito (no un CHECK/Enum): nuevas piezas (narrativa de plan,
        # estimación de recursos) se agregan sin migración, esto es telemetría
        # de apoyo, no un dato que el motor de reglas consulte para decidir nada.
        sa.Column("pieza", sa.String(), nullable=False),
        sa.Column("entrada_llm", sa.Text(), nullable=False),
        sa.Column("salida_llm", sa.Text(), nullable=False),
        sa.Column("correccion", sa.Text(), nullable=False),
        sa.Column("ruta_llm", sa.String(), nullable=True),
        sa.Column("creado_por", postgresql.UUID(as_uuid=True), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_correccion_ia_tenant_id", "correccion_ia", ["tenant_id"])
    op.create_index("ix_correccion_ia_pieza", "correccion_ia", ["pieza"])

    op.execute("ALTER TABLE correccion_ia ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE correccion_ia FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON correccion_ia
          USING (tenant_id = current_setting('app.tenant_id')::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON correccion_ia")
    op.drop_table("correccion_ia")

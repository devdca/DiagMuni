"""tenant.clave_geoestadistica + contexto_institucional.poblacion_total_fuente
-- primera integración con una fuente oficial externa (API de Indicadores de
INEGI), ver Plan_Arquitectura_DiagMuni_v2.md / nota de arquitectura "De
Municipio a Tres Órdenes".

`tenant.clave_geoestadistica`: clave de 5 dígitos INEGI (2 de entidad + 3 de
municipio, ej. "09004" = Cuajimalpa de Morelos, CDMX) -- nullable, un tenant
sin este dato simplemente no puede sincronizar con INEGI todavía (cierra de
forma segura en app/adaptadores/inegi/cliente_inegi.py, no un error duro). No aplica a
nivel_gobierno="federal" (una dependencia federal no tiene una sola clave
municipal) -- por eso no es NOT NULL ni siquiera para tenants nuevos.

`contexto_institucional.poblacion_total_fuente`: de dónde salió el valor
actual de `poblacion_total` -- "inegi_api" (lo escribió la sincronización) o
"manual" (lo escribió el funcionario por PUT /api/gobierno/contexto). NULL =
todavía no se ha llenado por ningún medio. Mismo criterio que
`porcentaje_tramites_en_linea_no_se_mide` (migración 0009): un campo hermano
que documenta la procedencia del dato en vez de mezclarla en el valor mismo
-- el dato de INEGI nunca sobreescribe en silencio lo que el funcionario ya
capturó a mano (ver app/aplicacion/sincronizacion_inegi.py).

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-10

"""

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

_FUENTES_VALIDAS = ("inegi_api", "manual")


def upgrade() -> None:
    op.add_column("tenant", sa.Column("clave_geoestadistica", sa.String(length=5), nullable=True))
    op.add_column(
        "contexto_institucional", sa.Column("poblacion_total_fuente", sa.String(), nullable=True)
    )
    op.create_check_constraint(
        "ck_contexto_institucional_poblacion_total_fuente_valida",
        "contexto_institucional",
        f"poblacion_total_fuente IS NULL OR poblacion_total_fuente IN "
        f"({', '.join(repr(f) for f in _FUENTES_VALIDAS)})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_contexto_institucional_poblacion_total_fuente_valida", "contexto_institucional")
    op.drop_column("contexto_institucional", "poblacion_total_fuente")
    op.drop_column("tenant", "clave_geoestadistica")

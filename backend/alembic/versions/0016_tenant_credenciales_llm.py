"""tenant: 4 columnas nuevas para que cada gobierno traiga su propia
credencial de IA (BYOK) -- en el despliegue real el operador no deja ninguna
API key propia configurada, así que cada tenant debe poder guardar la suya
por proveedor, para las 3 piezas de IA (F1/F3/F9).

`proveedor_llm_preferido`: cuál cascada de rutas usar para F3 (ver
_PROVEEDORES_RUTAS en app/adaptadores/llm/config.py). CHECK constraint, no
Enum nativo de Postgres -- agregar/quitar un proveedor soportado es un
ALTER TABLE normal, sin la restricción de ALTER TYPE ADD VALUE que no puede
usarse en la misma transacción en que se agrega (ver migración 0011).

`deepseek_api_key_cifrada` / `anthropic_api_key_cifrada`: cifradas con
Fernet (app/core/cifrado.py) usando TENANT_SECRET_KEY -- nunca texto plano,
nunca se devuelven en claro por la API una vez guardadas.

`ollama_api_base`: URL del propio servidor Ollama del tenant si autohospeda
inferencia local -- no es secreto (solo host:puerto), no se cifra.

Todas nullable=True sin server_default -- un tenant nuevo no debe heredar
ninguna credencial ni preferencia que nadie configuró.

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-09

"""

import sqlalchemy as sa

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

_PROVEEDORES_VALIDOS = ("anthropic", "deepseek", "local")


def upgrade() -> None:
    op.add_column("tenant", sa.Column("proveedor_llm_preferido", sa.String(), nullable=True))
    op.create_check_constraint(
        "ck_tenant_proveedor_llm_preferido_valido",
        "tenant",
        "proveedor_llm_preferido IS NULL OR proveedor_llm_preferido IN "
        f"({', '.join(repr(p) for p in _PROVEEDORES_VALIDOS)})",
    )
    op.add_column("tenant", sa.Column("deepseek_api_key_cifrada", sa.String(), nullable=True))
    op.add_column("tenant", sa.Column("anthropic_api_key_cifrada", sa.String(), nullable=True))
    op.add_column("tenant", sa.Column("ollama_api_base", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_constraint("ck_tenant_proveedor_llm_preferido_valido", "tenant")
    op.drop_column("tenant", "proveedor_llm_preferido")
    op.drop_column("tenant", "deepseek_api_key_cifrada")
    op.drop_column("tenant", "anthropic_api_key_cifrada")
    op.drop_column("tenant", "ollama_api_base")

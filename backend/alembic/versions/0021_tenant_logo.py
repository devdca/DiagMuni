"""tenant.logo_content_type + tenant.logo_actualizado_en -- cada gobierno puede
subir su propio logo (PUT /api/gobierno/logo) para mostrarlo en la UI donde hoy
solo aparece `nombre` (encabezado, watermark del hero en Panel resumen).

El archivo en sí NO vive en esta tabla ni en ninguna otra -- vive en disco, bajo
`settings.logo_storage_dir` (volumen `diagmuni_logos_data`, ver docker-compose.yml
y app/adaptadores/almacenamiento/logo_storage.py para la justificación completa de
por qué un volumen y no un blob en Postgres). Estas dos columnas son metadata
mínima que sí necesita vivir en la base de datos:

- `logo_content_type`: qué Content-Type devolver en GET /api/gobierno/logo (el
  archivo en disco no lleva extensión ni metadata propia) -- CHECK constraint con
  la misma lista blanca (`image/png`, `image/jpeg`, `image/svg+xml`) que valida la
  subida en app/aplicacion/gestion_logo.py, para que un dato inconsistente no
  pueda entrar ni siquiera por un camino que se salte esa validación de aplicación.
- `logo_actualizado_en`: cuándo se subió por última vez -- el frontend lo manda
  como parte de la key de caché del logo ya descargado (mismo criterio que un
  ETag simplificado, sin implementar el header HTTP real todavía).

Ambas NULL = el tenant nunca subió un logo (la UI cae a mostrar `nombre`), nunca
un error -- mismo criterio que `clave_geoestadistica` (migración 0019): un dato
opcional real, no una feature a medio terminar.

Revision ID: 0021
Revises: 0020
Create Date: 2026-09-15

"""

import sqlalchemy as sa

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

_TIPOS_LOGO_VALIDOS = ("image/png", "image/jpeg", "image/svg+xml")


def upgrade() -> None:
    op.add_column("tenant", sa.Column("logo_content_type", sa.String(), nullable=True))
    op.add_column("tenant", sa.Column("logo_actualizado_en", sa.DateTime(), nullable=True))
    op.create_check_constraint(
        "ck_tenant_logo_content_type_valido",
        "tenant",
        f"logo_content_type IS NULL OR logo_content_type IN "
        f"({', '.join(repr(t) for t in _TIPOS_LOGO_VALIDOS)})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tenant_logo_content_type_valido", "tenant")
    op.drop_column("tenant", "logo_actualizado_en")
    op.drop_column("tenant", "logo_content_type")

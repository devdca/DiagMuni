"""Persiste el logo de cada gobierno en disco (volumen `diagmuni_logos_data`),
un archivo por tenant -- no un blob en Postgres, mismas garantías de durabilidad
que `diagmuni_db_data` en este stack single-host, y se lee mucho más de lo que
se escribe. Tampoco se sirve por nginx como estático: nginx no tiene noción de
tenant/auth, y esta plataforma no hace excepciones al aislamiento por tenant."""

import os
import uuid
from pathlib import Path

from app.core.config import settings


def _ruta_logo(tenant_id: uuid.UUID) -> Path:
    return Path(settings.logo_storage_dir) / str(tenant_id)


def guardar_logo(tenant_id: uuid.UUID, contenido: bytes) -> None:
    """Escritura atómica: escribe a un archivo temporal en el mismo directorio y
    lo renombra sobre el destino final (`os.replace`, atómico tanto en
    POSIX/mismo filesystem como en NTFS). Sin esto, un request que se corta a
    la mitad podría dejar el archivo final truncado -- un lector concurrente
    (GET /api/gobierno/logo de otro request) nunca debe poder ver un estado a
    medio escribir."""
    ruta = _ruta_logo(tenant_id)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta_temporal = ruta.with_name(f"{ruta.name}.tmp-{os.getpid()}")
    ruta_temporal.write_bytes(contenido)
    os.replace(ruta_temporal, ruta)


def leer_logo(tenant_id: uuid.UUID) -> bytes | None:
    """None si el tenant nunca subió un logo -- quien llama decide si eso es un
    404 (ver app/adaptadores/http/gobierno_logo.py)."""
    ruta = _ruta_logo(tenant_id)
    if not ruta.is_file():
        return None
    return ruta.read_bytes()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# tamaño de pool declarado a propósito, no el default silencioso -- ver el
# manejo de TimeoutError en app/main.py
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)
# expire_on_commit=False: los atributos ya asignados en Python antes del commit
# (más los server_default que Postgres devuelve vía RETURNING en el propio flush)
# siguen siendo válidos después — evita que acceder a un atributo tras el commit
# dispare una recarga en una transacción nueva, donde app.tenant_id (RLS) ya no
# está fijado (ver app/db/rls.py, fijar_contexto_tenant).
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

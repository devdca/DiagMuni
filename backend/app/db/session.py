from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
# expire_on_commit=False: los atributos ya asignados en Python antes del commit
# (más los server_default que Postgres devuelve vía RETURNING en el propio flush)
# siguen siendo válidos después — evita que acceder a un atributo tras el commit
# dispare una recarga en una transacción nueva, donde app.tenant_id (RLS) ya no
# está fijado (ver app/db/rls.py, fijar_contexto_tenant).
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# H-12 (auditoría de seguridad): 15 conexiones (5 + 10 de overflow) es una
# decisión consciente para el piso de hardware de un piloto (2 vCPU / 2GB RAM,
# un solo proceso uvicorn sin --workers, ver docs/runbook-despliegue.md) -- no
# el default silencioso de SQLAlchemy. La propia auditoría midió el punto de
# quiebre real: 60 peticiones concurrentes autenticadas se sirven sin fallos,
# 200 agotan el pool (81% de fallos, ver TimeoutError en app/main.py). Si el
# despliegue crece a más gobiernos o más tráfico concurrente, hay que volver a
# medir con carga real antes de subir estos números a ciegas.
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

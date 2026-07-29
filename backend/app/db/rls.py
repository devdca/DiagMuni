from collections.abc import Generator
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal


def fijar_contexto_tenant(db: Session, tenant_id: UUID) -> None:
    """Fija app.tenant_id para la transacción ACTUAL de `db` (docs/backend-schema.md,
    "Políticas RLS"; docs/TRD.md, "Multi-tenancy").

    Se usa set_config(..., is_local=true) en vez de SET a secas: el tercer argumento
    hace que el valor se resetee solo al terminar la transacción, en vez de quedar
    pegado a la conexión física cuando vuelve al pool — sin esto, una conexión
    reusada por otro request podría heredar el tenant_id del request anterior.

    Contrapartida real de is_local=true, encontrada corriendo el flujo completo
    (no solo en teoría): **cada `db.commit()` (o rollback) termina la transacción y
    resetea el valor.** Cualquier código que haga más de un commit dentro de la
    misma sesión (ver app/jobs/plan_job.py) debe volver a llamar a esta función
    después de cada uno, antes de la siguiente consulta con RLS.
    """
    db.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": str(tenant_id)})


def abrir_sesion_tenant(tenant_id: UUID) -> Session:
    """Abre una sesión y fija el contexto de tenant. Quien la llama es responsable
    de cerrarla (db.close())."""
    db = SessionLocal()
    fijar_contexto_tenant(db, tenant_id)
    return db


def tenant_scoped_session(tenant_id: UUID) -> Generator[Session, None, None]:
    """Variante generador para usarse con FastAPI Depends (ver app/api/deps.py)."""
    db = abrir_sesion_tenant(tenant_id)
    try:
        yield db
    finally:
        db.close()

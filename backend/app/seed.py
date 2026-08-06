"""Datos semilla (docs/plan-implementacion.md, tarea B4): 2 tenants (MX y UY, para
ejercitar ambas ramas normativas), 1 usuario cada uno, 3 trámites de prueba cada uno.

Fixture de desarrollo/pruebas únicamente — nunca fuente de verdad para datos de un
municipio o intendencia real. Se niega a correr si ENVIRONMENT=production.

Uso: python -m app.seed
"""

from sqlalchemy import text

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Tenant, Tramite, Usuario

PASSWORD_PRUEBA = "cambiar123"


def _set_tenant(db, tenant_id) -> None:
    """Mismo mecanismo que app/db/rls.py — necesario porque las tablas con RLS
    tienen FORCE ROW LEVEL SECURITY (ver migración 0001), así que ni siquiera el
    dueño de la tabla puede insertar sin fijar app.tenant_id primero."""
    db.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": str(tenant_id)})


def run() -> None:
    if settings.environment == "production":
        raise RuntimeError(
            "seed.py crea un usuario con password fijo ('cambiar123') conocido públicamente en el "
            "repo — nunca debe correr contra producción. ENVIRONMENT=production detectado, abortando."
        )

    db = SessionLocal()
    try:
        tenant_mx = Tenant(nombre="Municipio de Prueba (MX)", clave="prueba-mx", pais="mx")
        tenant_uy = Tenant(nombre="Intendencia de Prueba (UY)", clave="prueba-uy", pais="uy")
        db.add_all([tenant_mx, tenant_uy])
        db.flush()  # tenant no tiene RLS — puede insertarse sin fijar app.tenant_id

        _set_tenant(db, tenant_mx.id)
        db.add(
            Usuario(
                tenant_id=tenant_mx.id,
                email="funcionario@prueba.mx",
                password_hash=hash_password(PASSWORD_PRUEBA),
                nombre="Funcionario de Prueba MX",
            )
        )
        db.add_all(
            [
                Tramite(tenant_id=tenant_mx.id, nombre="Licencia de funcionamiento", descripcion="Trámite de prueba"),
                Tramite(
                    tenant_id=tenant_mx.id,
                    nombre="Registro civil - acta de nacimiento",
                    descripcion="Trámite de prueba",
                ),
                Tramite(tenant_id=tenant_mx.id, nombre="Permiso de construcción", descripcion="Trámite de prueba"),
            ]
        )
        db.flush()

        _set_tenant(db, tenant_uy.id)
        db.add(
            Usuario(
                tenant_id=tenant_uy.id,
                email="funcionario@prueba.uy",
                password_hash=hash_password(PASSWORD_PRUEBA),
                nombre="Funcionario de Prueba UY",
            )
        )
        db.add_all(
            [
                Tramite(tenant_id=tenant_uy.id, nombre="Habilitación comercial", descripcion="Trámite de prueba"),
                Tramite(
                    tenant_id=tenant_uy.id, nombre="Certificado de empadronamiento", descripcion="Trámite de prueba"
                ),
                Tramite(tenant_id=tenant_uy.id, nombre="Permiso de obra", descripcion="Trámite de prueba"),
            ]
        )
        db.flush()

        db.commit()
        print(f"Semilla creada. tenant MX={tenant_mx.id}  tenant UY={tenant_uy.id}")
        print(f"Password de prueba (ambos usuarios): {PASSWORD_PRUEBA}")
    finally:
        db.close()


if __name__ == "__main__":
    run()

"""Datos semilla (docs/plan-implementacion.md, tarea B4): 2 tenants (MX y UY, para
ejercitar ambas ramas normativas), 1 usuario cada uno, 3 trámites de prueba cada uno.

Fixture de desarrollo/pruebas únicamente — nunca fuente de verdad para datos de un
municipio o intendencia real. Se niega a correr si ENVIRONMENT=production.

El tenant y el usuario de cada gobierno de prueba se crean con `crear_gobierno`
(app/bootstrap_tenant.py) — la misma función que usa la herramienta de producción
para el alta de un gobierno real, en vez de construir `Tenant`/`Usuario` por su
cuenta: un solo camino de creación, sin dos implementaciones que puedan
desincronizarse. Por eso cada corrida genera una contraseña nueva por usuario
(`generar_password_legible()`, app/core/security.py) — nunca una constante fija,
ni siquiera en un fixture de desarrollo. Idempotente: si ya existe, no crea
trámites duplicados.

Uso: python -m app.seed
"""

from app.bootstrap_tenant import crear_gobierno
from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Tramite


def run() -> None:
    if settings.environment == "production":
        raise RuntimeError(
            "seed.py crea usuarios de prueba con datos ficticios — nunca debe correr contra "
            "producción. ENVIRONMENT=production detectado, abortando."
        )

    db = SessionLocal()
    try:
        resultado_mx = crear_gobierno(
            db,
            nombre="Municipio de Prueba (MX)",
            clave="prueba-mx",
            pais="mx",
            email="funcionario@prueba.mx",
            nombre_funcionario="Funcionario de Prueba MX",
        )
        if resultado_mx is not None:
            tenant_mx, _usuario_mx, password_mx = resultado_mx
            db.add_all(
                [
                    Tramite(
                        tenant_id=tenant_mx.id, nombre="Licencia de funcionamiento", descripcion="Trámite de prueba"
                    ),
                    Tramite(
                        tenant_id=tenant_mx.id,
                        nombre="Registro civil - acta de nacimiento",
                        descripcion="Trámite de prueba",
                    ),
                    Tramite(
                        tenant_id=tenant_mx.id, nombre="Permiso de construcción", descripcion="Trámite de prueba"
                    ),
                ]
            )
            db.flush()

        resultado_uy = crear_gobierno(
            db,
            nombre="Intendencia de Prueba (UY)",
            clave="prueba-uy",
            pais="uy",
            email="funcionario@prueba.uy",
            nombre_funcionario="Funcionario de Prueba UY",
        )
        if resultado_uy is not None:
            tenant_uy, _usuario_uy, password_uy = resultado_uy
            db.add_all(
                [
                    Tramite(tenant_id=tenant_uy.id, nombre="Habilitación comercial", descripcion="Trámite de prueba"),
                    Tramite(
                        tenant_id=tenant_uy.id,
                        nombre="Certificado de empadronamiento",
                        descripcion="Trámite de prueba",
                    ),
                    Tramite(tenant_id=tenant_uy.id, nombre="Permiso de obra", descripcion="Trámite de prueba"),
                ]
            )
            db.flush()

        db.commit()

        if resultado_mx is None and resultado_uy is None:
            print("Los tenants de prueba ('prueba-mx', 'prueba-uy') ya existían. No se creó nada nuevo.")
            return

        print("Semilla creada. Esta contraseña no se vuelve a mostrar -- anótela ahora si la necesita:")
        if resultado_mx is not None:
            print(f"  tenant MX={resultado_mx[0].id}  funcionario@prueba.mx -> {resultado_mx[2]}")
        else:
            print("  tenant 'prueba-mx' ya existía -- no se tocó.")
        if resultado_uy is not None:
            print(f"  tenant UY={resultado_uy[0].id}  funcionario@prueba.uy -> {resultado_uy[2]}")
        else:
            print("  tenant 'prueba-uy' ya existía -- no se tocó.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()

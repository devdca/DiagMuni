"""Alta de un gobierno nuevo (tenant + primer usuario) al adoptar DiagMuni --
herramienta de producción (docs/plan-implementacion-alta-gobierno.md), no un
fixture de desarrollo (ver app/seed.py, que reutiliza `crear_gobierno` de este
módulo en vez de construir Tenant/Usuario por su cuenta).

Uso:
  python -m app.bootstrap_tenant crear-gobierno --nombre "Intendencia de Canelones" \
    --clave canelones --pais uy --email maria.perez@canelones.gub.uy \
    --nombre-funcionario "María Pérez"
  python -m app.bootstrap_tenant agregar-funcionario --clave canelones \
    --email juan.gonzalez@canelones.gub.uy --nombre "Juan González"
  python -m app.bootstrap_tenant resetear-password --clave canelones \
    --email maria.perez@canelones.gub.uy

Los tres subcomandos generan siempre una contraseña aleatoria nueva
(`generar_password_legible()`, app/core/security.py) -- ninguno acepta una
contraseña como argumento, para que nunca exista una contraseña fija que
filtrar (docs/plan-implementacion-alta-gobierno.md, sección 2 y 5).
"""

import argparse
import re
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import generar_password_legible, hash_password
from app.db.rls import fijar_contexto_tenant
from app.db.session import SessionLocal
from app.models import Tenant, Usuario

_CLAVE_VALIDA = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_EMAIL_VALIDO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PAISES_SOPORTADOS = ("mx", "uy")


def _normalizar_clave(clave: str) -> str:
    return clave.strip().lower()


def crear_gobierno(
    db: Session, *, nombre: str, clave: str, pais: str, email: str, nombre_funcionario: str
) -> tuple[Tenant, Usuario, str] | None:
    """Crea un tenant y su primer usuario, con una contraseña generada (nunca fija).

    Idempotente: si ya existe un tenant con esa `clave`, no escribe nada y devuelve
    `None` -- quien llama decide qué mensaje mostrar. No hace `commit()`: quien
    llama decide cuándo confirmar la transacción (docs/plan-implementacion-
    alta-gobierno.md, sección 4)."""
    clave = _normalizar_clave(clave)
    nombre = nombre.strip()
    nombre_funcionario = nombre_funcionario.strip()
    email = email.strip()

    if not nombre:
        raise ValueError("El nombre del gobierno no puede estar vacío.")
    if not nombre_funcionario:
        raise ValueError("El nombre del funcionario no puede estar vacío.")
    if pais not in _PAISES_SOPORTADOS:
        raise ValueError(f"País '{pais}' no soportado -- use 'mx' o 'uy'.")
    if not _CLAVE_VALIDA.match(clave):
        raise ValueError(
            f"La clave '{clave}' no es válida -- solo minúsculas, números y guiones simples "
            "entre palabras, sin empezar ni terminar en guion."
        )
    if not _EMAIL_VALIDO.match(email):
        raise ValueError(f"El email '{email}' no tiene un formato válido.")

    existente = db.execute(select(Tenant).where(Tenant.clave == clave)).scalar_one_or_none()
    if existente is not None:
        return None

    tenant = Tenant(nombre=nombre, clave=clave, pais=pais)
    db.add(tenant)
    db.flush()  # tenant no tiene RLS propio -- puede insertarse sin fijar app.tenant_id

    fijar_contexto_tenant(db, tenant.id)  # usuario sí tiene FORCE ROW LEVEL SECURITY

    password = generar_password_legible()
    usuario = Usuario(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password(password),
        nombre=nombre_funcionario,
    )
    db.add(usuario)
    db.flush()

    return tenant, usuario, password


def agregar_funcionario(
    db: Session, *, clave: str, email: str, nombre_funcionario: str
) -> tuple[Tenant, Usuario, str] | None:
    """Agrega un funcionario nuevo a un gobierno ya existente, con una contraseña
    generada (nunca fija) -- alcance futuro de docs/plan-implementacion-alta-
    gobierno.md sección 7, ahora implementado (sección 12). Idempotente: si el
    tenant no existe, o si ya existe un usuario con ese email en ese tenant, no
    escribe nada y devuelve `None` -- quien llama decide qué mensaje mostrar (los
    dos motivos exigen una acción distinta del operador, ver
    `_comando_agregar_funcionario`). No hace `commit()`.

    A diferencia de `crear_gobierno`, no valida `clave` contra `_CLAVE_VALIDA`
    -- opera sobre un tenant ya existente (mismo criterio que `resetear_password`):
    una clave con formato inválido simplemente no encuentra ningún tenant y cae en
    el mismo `None` que "tenant inexistente".

    Fuera de alcance a propósito: no acepta `--rol` (el enum de `Usuario.rol` solo
    tiene "funcionario" hoy, un parámetro sería código muerto); no edita un
    funcionario existente; no desactiva/elimina uno -- solo altas nuevas. Sin
    límite de funcionarios por tenant."""
    clave = _normalizar_clave(clave)
    email = email.strip()
    nombre_funcionario = nombre_funcionario.strip()

    if not nombre_funcionario:
        raise ValueError("El nombre del funcionario no puede estar vacío.")
    if not _EMAIL_VALIDO.match(email):
        raise ValueError(f"El email '{email}' no tiene un formato válido.")

    tenant = db.execute(select(Tenant).where(Tenant.clave == clave)).scalar_one_or_none()
    if tenant is None:
        return None

    fijar_contexto_tenant(db, tenant.id)  # usuario sí tiene FORCE ROW LEVEL SECURITY
    existente = db.execute(
        select(Usuario).where(Usuario.tenant_id == tenant.id, Usuario.email == email)
    ).scalar_one_or_none()
    if existente is not None:
        return None

    password = generar_password_legible()
    usuario = Usuario(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password(password),
        nombre=nombre_funcionario,
    )
    db.add(usuario)
    db.flush()

    return tenant, usuario, password


def resetear_password(db: Session, *, clave: str, email: str) -> str | None:
    """Genera una contraseña nueva para un usuario existente. No crea nada: si el
    tenant o el usuario no existen, devuelve `None` sin escribir."""
    clave = _normalizar_clave(clave)
    email = email.strip()

    tenant = db.execute(select(Tenant).where(Tenant.clave == clave)).scalar_one_or_none()
    if tenant is None:
        return None

    fijar_contexto_tenant(db, tenant.id)
    usuario = db.execute(
        select(Usuario).where(Usuario.tenant_id == tenant.id, Usuario.email == email)
    ).scalar_one_or_none()
    if usuario is None:
        return None

    password = generar_password_legible()
    usuario.password_hash = hash_password(password)
    db.flush()
    return password


def _advertencia_password(lineas: list[str]) -> None:
    print("=" * 68)
    print("ADVERTENCIA: esta contraseña no se vuelve a mostrar. Anótela ahora")
    print("y entréguela a la contraparte técnica por un canal seguro.")
    print("=" * 68)
    for linea in lineas:
        print(linea)
    print("=" * 68)


def _comando_crear_gobierno(args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        resultado = crear_gobierno(
            db,
            nombre=args.nombre,
            clave=args.clave,
            pais=args.pais,
            email=args.email,
            nombre_funcionario=args.nombre_funcionario,
        )
        if resultado is None:
            db.rollback()
            print(f"Ya existe un gobierno con la clave '{_normalizar_clave(args.clave)}'. No se creó nada nuevo.")
            return 1

        tenant, usuario, password = resultado
        db.commit()
        _advertencia_password(
            [
                f"Gobierno: {tenant.nombre} (clave: {tenant.clave})",
                f"Funcionario: {usuario.nombre} <{usuario.email}>",
                f"Contraseña de arranque: {password}",
            ]
        )
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _comando_agregar_funcionario(args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        resultado = agregar_funcionario(
            db, clave=args.clave, email=args.email, nombre_funcionario=args.nombre_funcionario
        )
        if resultado is None:
            db.rollback()
            clave = _normalizar_clave(args.clave)
            # Los dos motivos de `None` exigen una acción opuesta del operador
            # (dar de alta el gobierno primero vs. usar resetear-password) --
            # a diferencia de resetear_password, no se colapsan en un solo mensaje.
            tenant = db.execute(select(Tenant).where(Tenant.clave == clave)).scalar_one_or_none()
            if tenant is None:
                print(f"No existe ningún gobierno con la clave '{clave}'. Use 'crear-gobierno' primero.")
            else:
                print(
                    f"Ya existe un funcionario con el email '{args.email}' en el gobierno con clave "
                    f"'{clave}'. No se creó nada nuevo -- use 'resetear-password' si perdió su acceso."
                )
            return 1

        tenant, usuario, password = resultado
        db.commit()
        _advertencia_password(
            [
                f"Gobierno: {tenant.nombre} (clave: {tenant.clave})",
                f"Funcionario: {usuario.nombre} <{usuario.email}>",
                f"Contraseña de arranque: {password}",
            ]
        )
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _comando_resetear_password(args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        password = resetear_password(db, clave=args.clave, email=args.email)
        if password is None:
            db.rollback()
            clave = _normalizar_clave(args.clave)
            print(f"No se encontró el usuario '{args.email}' en el gobierno con clave '{clave}'.")
            return 1

        db.commit()
        _advertencia_password([f"Nueva contraseña para {args.email}: {password}"])
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Alta y mantenimiento del primer usuario de un gobierno.")
    subparsers = parser.add_subparsers(dest="comando", required=True)

    crear = subparsers.add_parser("crear-gobierno", help="Crea un tenant nuevo y su primer usuario.")
    crear.add_argument("--nombre", required=True, help="Nombre del gobierno (municipio o intendencia).")
    crear.add_argument("--clave", required=True, help="Identificador corto único que el funcionario usa en login.")
    crear.add_argument("--pais", required=True, choices=list(_PAISES_SOPORTADOS))
    crear.add_argument("--email", required=True, help="Email del primer funcionario.")
    crear.add_argument("--nombre-funcionario", required=True, dest="nombre_funcionario")
    crear.set_defaults(func=_comando_crear_gobierno)

    agregar = subparsers.add_parser(
        "agregar-funcionario", help="Agrega un funcionario nuevo a un gobierno ya existente."
    )
    agregar.add_argument("--clave", required=True, help="Clave del gobierno ya existente.")
    agregar.add_argument("--email", required=True, help="Email del nuevo funcionario.")
    agregar.add_argument("--nombre", required=True, dest="nombre_funcionario", help="Nombre del nuevo funcionario.")
    agregar.set_defaults(func=_comando_agregar_funcionario)

    resetear = subparsers.add_parser(
        "resetear-password", help="Genera una contraseña nueva para un usuario existente."
    )
    resetear.add_argument("--clave", required=True)
    resetear.add_argument("--email", required=True)
    resetear.set_defaults(func=_comando_resetear_password)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

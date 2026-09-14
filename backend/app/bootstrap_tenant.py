"""Alta de un gobierno nuevo (tenant + primer usuario) al adoptar DiagMuni --
herramienta de producción (docs/plan-implementacion-alta-gobierno.md), no un
fixture de desarrollo (ver app/seed.py, que reutiliza `crear_gobierno` de este
módulo en vez de construir Tenant/Usuario por su cuenta).

Uso:
  python -m app.bootstrap_tenant crear-gobierno --nombre "Ayuntamiento de Querétaro" \
    --clave queretaro --pais mx --email maria.perez@queretaro.gob.mx \
    --nombre-funcionario "María Pérez"
  python -m app.bootstrap_tenant agregar-funcionario --clave queretaro \
    --email juan.gonzalez@queretaro.gob.mx --nombre "Juan González"
  python -m app.bootstrap_tenant resetear-password --clave queretaro \
    --email maria.perez@queretaro.gob.mx

Los tres subcomandos generan siempre una contraseña aleatoria nueva
(`generar_password_legible()`, app/core/security.py) -- ninguno acepta una
contraseña como argumento, para que nunca exista una contraseña fija que
filtrar (docs/plan-implementacion-alta-gobierno.md, sección 2 y 5).

Toda la lógica de creación/gestión de usuarios vive en
`app/aplicacion/gestion_usuarios.py` (capa de aplicación, compartida con el
panel de administración vía HTTP) -- este módulo es solo el adaptador de línea
de comandos: parsea argumentos, abre/cierra la sesión y decide qué imprimir.
"""

import argparse
import sys

from app.aplicacion.gestion_usuarios import (
    PAISES_SOPORTADOS,
    agregar_funcionario,
    crear_gobierno,
    normalizar_clave,
    resetear_password,
)
from app.db.session import SessionLocal


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
            print(f"Ya existe un gobierno con la clave '{normalizar_clave(args.clave)}'. No se creó nada nuevo.")
            return 1

        tenant, usuario, password = resultado
        db.commit()
        _advertencia_password(
            [
                f"Gobierno: {tenant.nombre} (clave: {tenant.clave})",
                f"Administrador: {usuario.nombre} <{usuario.email}>",
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
            clave = normalizar_clave(args.clave)
            # Los dos motivos de `None` exigen una acción opuesta del operador
            # (dar de alta el gobierno primero vs. usar resetear-password) --
            # a diferencia de resetear_password, no se colapsan en un solo mensaje.
            from sqlalchemy import select

            from app.models import Tenant

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
            clave = normalizar_clave(args.clave)
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

    crear = subparsers.add_parser("crear-gobierno", help="Crea un tenant nuevo y su primer usuario (administrador).")
    crear.add_argument("--nombre", required=True, help="Nombre del gobierno (municipio o intendencia).")
    crear.add_argument("--clave", required=True, help="Identificador corto único que el funcionario usa en login.")
    crear.add_argument("--pais", required=True, choices=list(PAISES_SOPORTADOS))
    crear.add_argument("--email", required=True, help="Email del primer usuario (rol administrador).")
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

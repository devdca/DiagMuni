"""Alta y gestión de usuarios de un gobierno -- capa de aplicación (casos de uso),
compartida por dos adaptadores que nunca duplican esta lógica (docs/TRD.md,
"Alta de un gobierno nuevo": "bootstrap_tenant.py concentra todo el código de
creación/gestión de usuarios del proyecto... sin una segunda copia en ningún
otro archivo" -- ahora esa concentración vive aquí, no en la CLI):

- `app/bootstrap_tenant.py`: la CLI de alta inicial, opera por `clave` de tenant
  porque corre sin una sesión HTTP autenticada todavía.
- `app/adaptadores/http/admin_usuarios.py`: el panel de administración, opera por
  `tenant_id` ya resuelto por el JWT de un `admin_gobierno` autenticado.

Ambos llaman a las funciones de este módulo; ninguno reconstruye `Usuario` por su
cuenta.
"""

import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import generar_password_legible, hash_password, verify_password
from app.db.rls import fijar_contexto_tenant
from app.models import Tenant, Usuario
from app.models.usuario import ROLES_VALIDOS

EMAIL_VALIDO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CLAVE_VALIDA = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
PAISES_SOPORTADOS = ("mx", "uy")


def normalizar_clave(clave: str) -> str:
    return clave.strip().lower()


def _crear_fila_usuario(
    db: Session, *, tenant_id: UUID, email: str, nombre: str, rol: str = "funcionario"
) -> tuple[Usuario, str]:
    """Único lugar del proyecto que instancia `Usuario` para un alta -- todo alta
    (CLI o HTTP) termina aquí, con una contraseña generada nueva (nunca fija)."""
    password = generar_password_legible()
    usuario = Usuario(tenant_id=tenant_id, email=email, password_hash=hash_password(password), nombre=nombre, rol=rol)
    db.add(usuario)
    db.flush()
    return usuario, password


# --- Adaptador CLI (app/bootstrap_tenant.py): opera por `clave`, sin sesión ------
# --- HTTP previa (alta del primer gobierno, antes de que exista ningún JWT). -----


def crear_gobierno(
    db: Session, *, nombre: str, clave: str, pais: str, email: str, nombre_funcionario: str
) -> tuple[Tenant, Usuario, str] | None:
    """Crea un tenant y su primer usuario (rol `admin_gobierno`: alguien tiene que
    poder gestionar el gobierno desde el primer día, sin depender de la CLI para
    todo lo que siga). Idempotente por `clave`: si ya existe, no escribe nada y
    devuelve `None`. No hace `commit()`: quien llama decide cuándo confirmar."""
    clave = normalizar_clave(clave)
    nombre = nombre.strip()
    nombre_funcionario = nombre_funcionario.strip()
    email = email.strip()

    if not nombre:
        raise ValueError("El nombre del gobierno no puede estar vacío.")
    if not nombre_funcionario:
        raise ValueError("El nombre del funcionario no puede estar vacío.")
    if pais not in PAISES_SOPORTADOS:
        raise ValueError(f"País '{pais}' no soportado -- use 'mx' o 'uy'.")
    if not CLAVE_VALIDA.match(clave):
        raise ValueError(
            f"La clave '{clave}' no es válida -- solo minúsculas, números y guiones simples "
            "entre palabras, sin empezar ni terminar en guion."
        )
    if not EMAIL_VALIDO.match(email):
        raise ValueError(f"El email '{email}' no tiene un formato válido.")

    existente = db.execute(select(Tenant).where(Tenant.clave == clave)).scalar_one_or_none()
    if existente is not None:
        return None

    tenant = Tenant(nombre=nombre, clave=clave, pais=pais)
    db.add(tenant)
    db.flush()  # tenant no tiene RLS propio -- puede insertarse sin fijar app.tenant_id

    fijar_contexto_tenant(db, tenant.id)  # usuario sí tiene FORCE ROW LEVEL SECURITY

    usuario, password = _crear_fila_usuario(
        db, tenant_id=tenant.id, email=email, nombre=nombre_funcionario, rol="admin_gobierno"
    )
    return tenant, usuario, password


def agregar_funcionario(
    db: Session, *, clave: str, email: str, nombre_funcionario: str
) -> tuple[Tenant, Usuario, str] | None:
    """Agrega un funcionario (rol `funcionario`) a un gobierno ya existente vía CLI.
    Idempotente por email duplicado dentro del mismo tenant. No hace `commit()`."""
    clave = normalizar_clave(clave)
    email = email.strip()
    nombre_funcionario = nombre_funcionario.strip()

    if not nombre_funcionario:
        raise ValueError("El nombre del funcionario no puede estar vacío.")
    if not EMAIL_VALIDO.match(email):
        raise ValueError(f"El email '{email}' no tiene un formato válido.")

    tenant = db.execute(select(Tenant).where(Tenant.clave == clave)).scalar_one_or_none()
    if tenant is None:
        return None

    fijar_contexto_tenant(db, tenant.id)
    existente = db.execute(
        select(Usuario).where(Usuario.tenant_id == tenant.id, Usuario.email == email)
    ).scalar_one_or_none()
    if existente is not None:
        return None

    usuario, password = _crear_fila_usuario(
        db, tenant_id=tenant.id, email=email, nombre=nombre_funcionario, rol="funcionario"
    )
    return tenant, usuario, password


def resetear_password(db: Session, *, clave: str, email: str) -> str | None:
    """Genera una contraseña nueva para un usuario existente (CLI, sin JWT). No
    crea nada: si el tenant o el usuario no existen, devuelve `None`."""
    clave = normalizar_clave(clave)
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


# --- Adaptador HTTP (app/adaptadores/http/admin_usuarios.py, .../perfil_usuario.py):
# --- operan por `tenant_id` ya resuelto y autenticado por un JWT válido. -----------


def _usuario_del_tenant(db: Session, *, tenant_id: UUID, usuario_id: UUID) -> Usuario | None:
    return db.execute(
        select(Usuario).where(Usuario.tenant_id == tenant_id, Usuario.id == usuario_id)
    ).scalar_one_or_none()


def _contar_admins_activos(db: Session, *, tenant_id: UUID, excluir_usuario_id: UUID) -> int:
    return db.execute(
        select(func.count())
        .select_from(Usuario)
        .where(
            Usuario.tenant_id == tenant_id,
            Usuario.rol == "admin_gobierno",
            Usuario.activo.is_(True),
            Usuario.id != excluir_usuario_id,
        )
    ).scalar_one()


def listar_usuarios(db: Session, tenant_id: UUID) -> list[Usuario]:
    return list(
        db.execute(select(Usuario).where(Usuario.tenant_id == tenant_id).order_by(Usuario.created_at)).scalars()
    )


def crear_usuario(db: Session, *, tenant_id: UUID, email: str, nombre: str, rol: str) -> tuple[Usuario, str] | None:
    """Alta de funcionario/administrador desde el panel de administración
    (`admin_gobierno` ya autenticado, `tenant_id` ya resuelto -- a diferencia de
    `agregar_funcionario`, nunca necesita volver a buscar el tenant por `clave`).
    `None` si ya existe un usuario con ese email en este mismo tenant."""
    email = email.strip()
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre no puede estar vacío.")
    if not EMAIL_VALIDO.match(email):
        raise ValueError(f"El email '{email}' no tiene un formato válido.")
    if rol not in ROLES_VALIDOS:
        raise ValueError(f"Rol '{rol}' no válido.")

    existente = db.execute(
        select(Usuario).where(Usuario.tenant_id == tenant_id, Usuario.email == email)
    ).scalar_one_or_none()
    if existente is not None:
        return None

    return _crear_fila_usuario(db, tenant_id=tenant_id, email=email, nombre=nombre, rol=rol)


def desactivar_usuario(db: Session, *, tenant_id: UUID, usuario_id: UUID) -> Usuario | None:
    """`None` si el usuario no existe en este tenant. Rechaza con `ValueError`
    desactivar al único administrador activo -- sin eso, un gobierno con un solo
    `admin_gobierno` podría quedar sin nadie que pueda reactivar a nadie."""
    usuario = _usuario_del_tenant(db, tenant_id=tenant_id, usuario_id=usuario_id)
    if usuario is None:
        return None
    if (
        usuario.rol == "admin_gobierno"
        and usuario.activo
        and _contar_admins_activos(db, tenant_id=tenant_id, excluir_usuario_id=usuario_id) == 0
    ):
        raise ValueError("No puedes desactivar al único administrador activo de este gobierno.")
    usuario.activo = False
    db.flush()
    return usuario


def reactivar_usuario(db: Session, *, tenant_id: UUID, usuario_id: UUID) -> Usuario | None:
    usuario = _usuario_del_tenant(db, tenant_id=tenant_id, usuario_id=usuario_id)
    if usuario is None:
        return None
    usuario.activo = True
    db.flush()
    return usuario


def cambiar_rol(db: Session, *, tenant_id: UUID, usuario_id: UUID, nuevo_rol: str) -> Usuario | None:
    """Mismo guard que `desactivar_usuario`: no permite quitarle `admin_gobierno`
    al único administrador activo del tenant."""
    if nuevo_rol not in ROLES_VALIDOS:
        raise ValueError(f"Rol '{nuevo_rol}' no válido.")
    usuario = _usuario_del_tenant(db, tenant_id=tenant_id, usuario_id=usuario_id)
    if usuario is None:
        return None
    if (
        usuario.rol == "admin_gobierno"
        and nuevo_rol != "admin_gobierno"
        and usuario.activo
        and _contar_admins_activos(db, tenant_id=tenant_id, excluir_usuario_id=usuario_id) == 0
    ):
        raise ValueError("No puedes quitarle el rol de administrador al único administrador activo de este gobierno.")
    usuario.rol = nuevo_rol
    db.flush()
    return usuario


def resetear_password_por_id(db: Session, *, tenant_id: UUID, usuario_id: UUID) -> str | None:
    """Reseteo disparado por un `admin_gobierno` desde el panel (a diferencia de
    `resetear_password`, que opera por `clave` desde la CLI)."""
    usuario = _usuario_del_tenant(db, tenant_id=tenant_id, usuario_id=usuario_id)
    if usuario is None:
        return None
    password = generar_password_legible()
    usuario.password_hash = hash_password(password)
    db.flush()
    return password


def cambiar_password_propia(
    db: Session, *, tenant_id: UUID, usuario_id: UUID, password_actual: str, password_nueva: str
) -> bool:
    """Autoservicio (`/api/usuarios/me/password`): exige la contraseña actual --
    a diferencia de un reseteo por un administrador, este es el propio dueño de
    la cuenta cambiándola. `ValueError` si la actual no coincide."""
    usuario = _usuario_del_tenant(db, tenant_id=tenant_id, usuario_id=usuario_id)
    if usuario is None:
        return False
    if not verify_password(password_actual, usuario.password_hash):
        raise ValueError("La contraseña actual no coincide.")
    usuario.password_hash = hash_password(password_nueva)
    db.flush()
    return True


def actualizar_nombre_propio(db: Session, *, tenant_id: UUID, usuario_id: UUID, nombre: str) -> Usuario | None:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre no puede estar vacío.")
    usuario = _usuario_del_tenant(db, tenant_id=tenant_id, usuario_id=usuario_id)
    if usuario is None:
        return None
    usuario.nombre = nombre
    db.flush()
    return usuario


def registrar_login(db: Session, usuario: Usuario) -> None:
    """Actualiza `ultimo_login_en` -- se llama desde `auth.py` justo después de
    verificar la contraseña, antes de emitir el JWT. No hace `commit()` (el login
    ya cierra su propia sesión; el caller decide)."""
    usuario.ultimo_login_en = datetime.now(UTC)
    db.flush()

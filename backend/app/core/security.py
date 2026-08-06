import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()

# Alfabeto sin caracteres visualmente ambiguos: dígitos 2-9 (sin 0/1), mayúsculas
# sin I/O, minúsculas sin i/l/o -- 55 símbolos en total.
_ALFABETO_PASSWORD_LEGIBLE = "23456789" "ABCDEFGHJKLMNPQRSTUVWXYZ" "abcdefghjkmnpqrstuvwxyz"
_LONGITUD_PASSWORD_LEGIBLE = 16
_TAMANO_BLOQUE_PASSWORD_LEGIBLE = 4


def generar_password_legible() -> str:
    """Contraseña aleatoria de arranque -- 16 caracteres del alfabeto de 55 símbolos
    de arriba (~92.5 bits de entropía), agrupada en bloques de 4 separados por guion
    para poder dictarla por teléfono o transcribirla sin ambigüedad. Los guiones son
    parte literal de la contraseña, no un separador a limpiar antes de usarla."""
    caracteres = [secrets.choice(_ALFABETO_PASSWORD_LEGIBLE) for _ in range(_LONGITUD_PASSWORD_LEGIBLE)]
    bloques = [
        "".join(caracteres[i : i + _TAMANO_BLOQUE_PASSWORD_LEGIBLE])
        for i in range(0, _LONGITUD_PASSWORD_LEGIBLE, _TAMANO_BLOQUE_PASSWORD_LEGIBLE)
    ]
    return "-".join(bloques)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_access_token(usuario_id: UUID, tenant_id: UUID, rol: str, nombre_gobierno: str, pais: str) -> str:
    # `pais` viaja en el JWT solo para que el frontend sepa qué mostrar (ej. qué
    # opciones de mecanismo_identidad ofrecer) -- ningún endpoint puede usar este
    # claim para decidir nada de seguridad: `pais` se vuelve a resolver siempre
    # desde `Tenant` en el servidor (ver app/api/asistente_captura.py).
    expire = datetime.now(UTC) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": str(usuario_id),
        "tenant_id": str(tenant_id),
        "nombre_gobierno": nombre_gobierno,
        "pais": pais,
        "rol": rol,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

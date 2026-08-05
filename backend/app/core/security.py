from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()


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

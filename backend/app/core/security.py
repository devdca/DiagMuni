import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()

# Claims fijos de emisor/audiencia -- defensa extra contra tokens de otro
# servicio firmados por error con el mismo secreto.
_JWT_ISSUER = "diagmuni-backend"
_JWT_AUDIENCE = "diagmuni-api"

# Alfabeto sin caracteres visualmente ambiguos: dígitos 2-9 (sin 0/1), mayúsculas
# sin I/O, minúsculas sin i/l/o -- 55 símbolos en total.
_ALFABETO_PASSWORD_LEGIBLE = "23456789" "ABCDEFGHJKLMNPQRSTUVWXYZ" "abcdefghjkmnpqrstuvwxyz"
_LONGITUD_PASSWORD_LEGIBLE = 16
_TAMANO_BLOQUE_PASSWORD_LEGIBLE = 4


def generar_password_legible() -> str:
    """16 caracteres del alfabeto de 55 símbolos (~92.5 bits), en bloques de 4
    separados por guion para dictar por teléfono. Los guiones son parte
    literal de la contraseña."""
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


def create_access_token(
    usuario_id: UUID, tenant_id: UUID, rol: str, nombre_gobierno: str, pais: str, nivel_gobierno: str
) -> str:
    # pais/nivel_gobierno viajan en el JWT solo para la UI -- nunca se usan para
    # decidir seguridad, siempre se resuelven de nuevo desde Tenant.
    expire = datetime.now(UTC) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": str(usuario_id),
        "tenant_id": str(tenant_id),
        "nombre_gobierno": nombre_gobierno,
        "pais": pais,
        "nivel_gobierno": nivel_gobierno,
        "rol": rol,
        "iss": _JWT_ISSUER,
        "aud": _JWT_AUDIENCE,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    # algorithms=["HS256"] fijo cierra la confusión de algoritmo de CVE-2026-48526
    # (nunca acepta RS/ES). issuer/audience + require rechazan un token sin esos
    # claims antes de llegar a deps.py.
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        issuer=_JWT_ISSUER,
        audience=_JWT_AUDIENCE,
        options={"require": ["exp", "iss", "aud", "sub"]},
    )

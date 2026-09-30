from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.rls import abrir_sesion_tenant, tenant_scoped_session
from app.models.usuario import Usuario

_bearer_scheme = HTTPBearer(auto_error=False)
_CREDENCIALES_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado"
)


@dataclass
class TokenData:
    usuario_id: UUID
    tenant_id: UUID
    rol: str


def get_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> TokenData:
    """Nunca confía en los claims del JWT solos -- resuelve el usuario real desde
    la BD, y `tenant_id`/`rol` en `TokenData` son siempre los de ese registro.

    `auto_error=False`: el default de `HTTPBearer` responde 403 sin header
    Authorization, distinto del 401 de token inválido (hallazgo Strix) -- se
    estandariza a 401 en ambos casos."""
    if credentials is None:
        raise _CREDENCIALES_INVALIDAS

    try:
        payload = decode_access_token(credentials.credentials)
        usuario_id = UUID(payload["sub"])
        tenant_id_claim = UUID(payload["tenant_id"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise _CREDENCIALES_INVALIDAS from exc

    # RLS forzado exige tenant_id fijado antes de leer -- la verificación real es
    # comparar usuario.tenant_id contra ese valor, abajo.
    db = abrir_sesion_tenant(tenant_id_claim)
    try:
        usuario = db.get(Usuario, usuario_id)
    finally:
        db.close()

    if usuario is None or usuario.tenant_id != tenant_id_claim:
        raise _CREDENCIALES_INVALIDAS

    # Se revisa en CADA request, no solo en login -- desactivar a alguien corta el
    # acceso de inmediato, sin esperar a que expire su JWT.
    if not usuario.activo:
        raise _CREDENCIALES_INVALIDAS

    return TokenData(usuario_id=usuario.id, tenant_id=usuario.tenant_id, rol=usuario.rol)


def get_db(token: Annotated[TokenData, Depends(get_current_token)]) -> Generator[Session, None, None]:
    """Sesión con app.tenant_id ya fijado (RLS) — usar en todo endpoint autenticado."""
    yield from tenant_scoped_session(token.tenant_id)


def requerir_admin(token: Annotated[TokenData, Depends(get_current_token)]) -> TokenData:
    """Dependencia adicional para los endpoints de administración del propio
    gobierno (RBAC, migración 0011) -- 403, no 404: la existencia de `/api/admin/*`
    no es secreta, solo el permiso para usarla."""
    if token.rol != "admin_gobierno":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requiere rol de administrador")
    return token

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

_bearer_scheme = HTTPBearer()
_CREDENCIALES_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado"
)


@dataclass
class TokenData:
    usuario_id: UUID
    tenant_id: UUID
    rol: str


def get_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
) -> TokenData:
    """Nunca confía en los claims del JWT por sí solos: un token con firma válida
    pero un `sub`/`tenant_id` inventados (o de un usuario real movido a otro
    tenant desde que se emitió) pasaría la sola verificación de firma. Aquí se
    resuelve el usuario real desde la base de datos y el `tenant_id`/`rol` que
    viajan en `TokenData` de ahí en más son siempre los de ese registro, nunca
    los del claim crudo."""
    try:
        payload = decode_access_token(credentials.credentials)
        usuario_id = UUID(payload["sub"])
        tenant_id_claim = UUID(payload["tenant_id"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise _CREDENCIALES_INVALIDAS from exc

    # RLS forzado en `usuario` exige un tenant_id fijado antes de poder leer la fila
    # -- se fija con el tenant_id reclamado por el propio token, igual que hace el
    # login (app/api/auth.py), y la verificación real ocurre abajo comparando
    # `usuario.tenant_id` contra ese mismo valor.
    db = abrir_sesion_tenant(tenant_id_claim)
    try:
        usuario = db.get(Usuario, usuario_id)
    finally:
        db.close()

    if usuario is None or usuario.tenant_id != tenant_id_claim:
        raise _CREDENCIALES_INVALIDAS

    return TokenData(usuario_id=usuario.id, tenant_id=usuario.tenant_id, rol=usuario.rol)


def get_db(token: Annotated[TokenData, Depends(get_current_token)]) -> Generator[Session, None, None]:
    """Sesión con app.tenant_id ya fijado (RLS) — usar en todo endpoint autenticado."""
    yield from tenant_scoped_session(token.tenant_id)

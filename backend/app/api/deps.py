from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.rls import tenant_scoped_session

_bearer_scheme = HTTPBearer()


@dataclass
class TokenData:
    usuario_id: UUID
    tenant_id: UUID
    rol: str


def get_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
) -> TokenData:
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado"
        ) from exc
    return TokenData(
        usuario_id=UUID(payload["sub"]),
        tenant_id=UUID(payload["tenant_id"]),
        rol=payload["rol"],
    )


def get_db(token: Annotated[TokenData, Depends(get_current_token)]) -> Generator[Session, None, None]:
    """Sesión con app.tenant_id ya fijado (RLS) — usar en todo endpoint autenticado."""
    yield from tenant_scoped_session(token.tenant_id)

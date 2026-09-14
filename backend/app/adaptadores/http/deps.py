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
    """Nunca confía en los claims del JWT por sí solos: un token con firma válida
    pero un `sub`/`tenant_id` inventados (o de un usuario real movido a otro
    tenant desde que se emitió) pasaría la sola verificación de firma. Aquí se
    resuelve el usuario real desde la base de datos y el `tenant_id`/`rol` que
    viajan en `TokenData` de ahí en más son siempre los de ese registro, nunca
    los del claim crudo.

    `auto_error=False` en `_bearer_scheme`: el default de `HTTPBearer` responde
    403 ("Not authenticated") cuando el header `Authorization` falta por
    completo, distinto del 401 que ya se usa para un token inválido/expirado --
    inconsistencia de status code sin implicación de seguridad real (la petición
    se rechaza antes de ejecutar cualquier operación en ambos casos), señalada
    por una revisión de seguridad externa (Strix) sobre los endpoints de
    archivar/eliminar trámite. Se estandariza a 401 en los dos casos."""
    if credentials is None:
        raise _CREDENCIALES_INVALIDAS

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

    # Se revisa en CADA request, no solo en el login: si un admin desactiva a un
    # funcionario a media jornada, ese funcionario pierde acceso de inmediato --
    # no hay que esperar a que expire su JWT (hasta 8h, ver settings.jwt_expire_hours).
    # Mismo 401 genérico que el resto de esta función, para no revelar por qué
    # (evita que alguien confirme por este medio que una cuenta existe pero está
    # desactivada).
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

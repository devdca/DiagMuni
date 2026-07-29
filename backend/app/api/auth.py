from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.security import create_access_token, verify_password
from app.db.rls import abrir_sesion_tenant
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    # `usuario` tiene RLS FORZADO (migración 0001): current_setting('app.tenant_id')
    # revienta si nunca se fijó en la sesión, así que el login no puede usar la
    # sesión "plana" de app/db/session.py. Se fija con el tenant_id que el propio
    # cliente declara al iniciar sesión ("selección de gobierno", docs/ux-brief.md,
    # pantalla 1) — es seguro porque el WHERE de abajo ya filtra por ese mismo
    # tenant_id: si no coincide con ningún usuario real, ambos (RLS y WHERE)
    # concuerdan en cero filas.
    db = abrir_sesion_tenant(payload.tenant_id)
    try:
        usuario = db.execute(
            select(Usuario).where(Usuario.tenant_id == payload.tenant_id, Usuario.email == payload.email)
        ).scalar_one_or_none()
    finally:
        db.close()

    if usuario is None or not verify_password(payload.password, usuario.password_hash):
        # Mensaje en lenguaje llano, sin código técnico (docs/ux-brief.md, pantalla 1).
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Las credenciales no coinciden")
    token = create_access_token(usuario.id, usuario.tenant_id, usuario.rol)
    return TokenResponse(access_token=token)

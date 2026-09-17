from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.aplicacion.gestion_usuarios import registrar_login
from app.core.rate_limit import LimitadorVentanaDeslizante, ip_cliente
from app.core.security import create_access_token, verify_password
from app.db.rls import abrir_sesion_tenant
from app.models.tenant import Tenant
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Más estricto que /api/gobiernos: un acierto aquí entrega sesión real (hallazgo
# Strix vuln-0001, brute-force sin protección).
INTENTOS_MAXIMOS_POR_VENTANA = 5
VENTANA_SEGUNDOS = 60.0

_limitador = LimitadorVentanaDeslizante(INTENTOS_MAXIMOS_POR_VENTANA, VENTANA_SEGUNDOS)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request) -> TokenResponse:
    # Antes de tocar la BD: un intento rechazado no gasta ni una consulta.
    if not _limitador.permitir_intento(ip_cliente(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Espera un momento e intenta de nuevo.",
        )

    # `usuario` tiene RLS forzado -- se fija con el tenant_id que declara el
    # cliente; seguro porque el WHERE de abajo filtra por el mismo tenant_id.
    db = abrir_sesion_tenant(payload.tenant_id)
    try:
        usuario = db.execute(
            select(Usuario).where(Usuario.tenant_id == payload.tenant_id, Usuario.email == payload.email)
        ).scalar_one_or_none()
        tenant = db.get(Tenant, payload.tenant_id)  # `tenant` no tiene RLS, es la raíz de aislamiento

        if usuario is None or tenant is None or not verify_password(payload.password, usuario.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Las credenciales no coinciden")
        # Mismo mensaje genérico: no confirma si la cuenta existe pero está desactivada.
        if not usuario.activo:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Las credenciales no coinciden")

        registrar_login(db, usuario)
        token = create_access_token(
            usuario.id, usuario.tenant_id, usuario.rol, tenant.nombre, tenant.pais, tenant.nivel_gobierno
        )
        db.commit()
    finally:
        db.close()

    return TokenResponse(access_token=token)

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.rate_limit import LimitadorVentanaDeslizante, ip_cliente
from app.core.security import create_access_token, verify_password
from app.db.rls import abrir_sesion_tenant
from app.models.tenant import Tenant
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Más estricto que /api/gobiernos (10/60s, app/api/gobiernos.py): un acierto aquí
# entrega una sesión real, no solo confirma que existe un gobierno -- objetivo de
# mayor valor para quien intenta adivinar por fuerza bruta (hallazgo de Strix,
# vuln-0001, "Missing brute-force protection on /api/auth/login").
INTENTOS_MAXIMOS_POR_VENTANA = 5
VENTANA_SEGUNDOS = 60.0

_limitador = LimitadorVentanaDeslizante(INTENTOS_MAXIMOS_POR_VENTANA, VENTANA_SEGUNDOS)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request) -> TokenResponse:
    # Se aplica antes de tocar la base de datos, para que los intentos
    # rechazados por el límite no gasten ni una consulta (mismo criterio que
    # /api/gobiernos, ver app/api/gobiernos.py).
    if not _limitador.permitir_intento(ip_cliente(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Espera un momento e intenta de nuevo.",
        )

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
        # `tenant` no tiene RLS (es la tabla raíz de aislamiento) -- se puede leer
        # con la misma sesión sin depender de app.tenant_id ya fijado arriba.
        tenant = db.get(Tenant, payload.tenant_id)
    finally:
        db.close()

    if usuario is None or tenant is None or not verify_password(payload.password, usuario.password_hash):
        # Mensaje en lenguaje llano, sin código técnico (docs/ux-brief.md, pantalla 1).
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Las credenciales no coinciden")
    token = create_access_token(usuario.id, usuario.tenant_id, usuario.rol, tenant.nombre, tenant.pais)
    return TokenResponse(access_token=token)

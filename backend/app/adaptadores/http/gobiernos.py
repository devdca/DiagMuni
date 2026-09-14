from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.rate_limit import LimitadorVentanaDeslizante, ip_cliente
from app.db.session import SessionLocal
from app.models.tenant import Tenant
from app.schemas.gobierno import GobiernoOut

router = APIRouter(prefix="/api/gobiernos", tags=["gobiernos"])

# Mitiga enumeración de `clave` por fuerza bruta (entregables/fase-2/
# identificacion-gobierno-login.md, sección 3). Ver app/core/rate_limit.py para
# el mecanismo (compartido con /api/auth/login).
INTENTOS_MAXIMOS_POR_VENTANA = 10
VENTANA_SEGUNDOS = 60.0

_limitador = LimitadorVentanaDeslizante(INTENTOS_MAXIMOS_POR_VENTANA, VENTANA_SEGUNDOS)


@router.get("/{clave}", response_model=GobiernoOut)
def resolver_gobierno(clave: str, request: Request) -> GobiernoOut:
    """Público, sin JWT (entregables/fase-2/identificacion-gobierno-login.md,
    sección 3) -- el funcionario todavía no tiene sesión en este paso del login,
    y este endpoint nunca expone nada de `usuario`."""
    if not _limitador.permitir_intento(ip_cliente(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Espera un momento e intenta de nuevo.",
        )

    clave_normalizada = clave.strip().lower()
    # `tenant` no tiene RLS (tabla raíz de aislamiento, docs/backend-schema.md) --
    # una sesión sin app.tenant_id fijado puede leerla sin problema.
    db = SessionLocal()
    try:
        tenant = db.execute(select(Tenant).where(Tenant.clave == clave_normalizada)).scalar_one_or_none()
    finally:
        db.close()

    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontramos un gobierno con esa clave")

    return GobiernoOut(tenant_id=tenant.id, nombre=tenant.nombre)

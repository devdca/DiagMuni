import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.tenant import Tenant
from app.schemas.gobierno import GobiernoOut

router = APIRouter(prefix="/api/gobiernos", tags=["gobiernos"])

# Ventana deslizante en memoria de proceso, sin dependencia nueva ni persistencia
# (entregables/fase-2/identificacion-gobierno-login.md, sección 3, nota del auditor
# de F2-diseño): suficiente para el volumen de un piloto (pocos gobiernos, tráfico
# bajo). Mitiga enumeración de `clave` por fuerza bruta. Se reinicia si el proceso
# reinicia -- aceptable para este propósito, a diferencia del contador de intentos
# de `job` (app/jobs/plan_job.py), que sí necesita sobrevivir un reinicio.
INTENTOS_MAXIMOS_POR_VENTANA = 10
VENTANA_SEGUNDOS = 60.0

_intentos_por_ip: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def _permitir_intento(ip: str, ahora: float | None = None, registro: dict[str, deque[float]] | None = None) -> bool:
    """True si `ip` todavía tiene cupo dentro de la ventana deslizante -- registra
    el intento actual si lo permite. `ahora`/`registro` son inyectables para poder
    testear sin depender del reloj real ni del estado global del módulo."""
    ahora = ahora if ahora is not None else time.monotonic()
    registro = _intentos_por_ip if registro is None else registro
    with _lock:
        intentos = registro[ip]
        limite_inferior = ahora - VENTANA_SEGUNDOS
        while intentos and intentos[0] < limite_inferior:
            intentos.popleft()
        if len(intentos) >= INTENTOS_MAXIMOS_POR_VENTANA:
            return False
        intentos.append(ahora)
        return True


def _ip_cliente(request: Request) -> str:
    # nginx (nginx/nginx.conf) fija X-Real-IP en producción; sin proxy por delante
    # (desarrollo local) cae al remitente directo de la conexión TCP.
    if request.client is None:
        return "desconocido"
    return request.headers.get("x-real-ip", request.client.host)


@router.get("/{clave}", response_model=GobiernoOut)
def resolver_gobierno(clave: str, request: Request) -> GobiernoOut:
    """Público, sin JWT (entregables/fase-2/identificacion-gobierno-login.md,
    sección 3) -- el funcionario todavía no tiene sesión en este paso del login,
    y este endpoint nunca expone nada de `usuario`."""
    if not _permitir_intento(_ip_cliente(request)):
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

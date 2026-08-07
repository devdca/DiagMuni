"""Ventana deslizante en memoria de proceso, sin dependencia nueva ni
persistencia -- suficiente para el volumen de un piloto (pocos gobiernos,
tráfico bajo). Se reinicia si el proceso reinicia -- aceptable para limitar
intentos por IP, a diferencia del contador de `job` (app/jobs/plan_job.py), que
sí necesita sobrevivir un reinicio.

Compartido entre `/api/gobiernos` y `/api/auth/login` (antes vivía solo en
`api/gobiernos.py`; ver hallazgo de Strix vuln-0001, "Missing brute-force
protection on /api/auth/login") para que el mismo mecanismo no quede duplicado
en dos routers y pueda desincronizarse en silencio si cambia."""

import threading
import time
from collections import defaultdict, deque

from fastapi import Request


class LimitadorVentanaDeslizante:
    def __init__(self, intentos_maximos: int, ventana_segundos: float) -> None:
        self.intentos_maximos = intentos_maximos
        self.ventana_segundos = ventana_segundos
        self._intentos_por_clave: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def permitir_intento(self, clave: str, ahora: float | None = None) -> bool:
        """True si `clave` todavía tiene cupo dentro de la ventana deslizante --
        registra el intento actual si lo permite. `ahora` es inyectable para
        poder testear sin depender del reloj real."""
        ahora = ahora if ahora is not None else time.monotonic()
        with self._lock:
            intentos = self._intentos_por_clave[clave]
            limite_inferior = ahora - self.ventana_segundos
            while intentos and intentos[0] < limite_inferior:
                intentos.popleft()
            if len(intentos) >= self.intentos_maximos:
                return False
            intentos.append(ahora)
            return True


def ip_cliente(request: Request) -> str:
    # nginx (nginx/nginx.conf) fija X-Real-IP en producción; sin proxy por delante
    # (desarrollo local) cae al remitente directo de la conexión TCP.
    if request.client is None:
        return "desconocido"
    return request.headers.get("x-real-ip", request.client.host)

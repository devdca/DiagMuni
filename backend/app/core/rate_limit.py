"""Ventana deslizante en memoria de proceso, sin dependencia nueva -- suficiente
para el volumen de un piloto. Se reinicia con el proceso (a diferencia de
`job`, que sí debe sobrevivir un reinicio). Compartida entre `/api/gobiernos` y
`/api/auth/login` (hallazgo Strix vuln-0001) para no duplicar el mecanismo."""

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
        """True si `clave` tiene cupo y registra el intento. `ahora` es
        inyectable para testear sin el reloj real."""
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
    # nginx fija X-Real-IP en producción; sin proxy (dev local) cae al remitente TCP directo.
    if request.client is None:
        return "desconocido"
    return request.headers.get("x-real-ip", request.client.host)

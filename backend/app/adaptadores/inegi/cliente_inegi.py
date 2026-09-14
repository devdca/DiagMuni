"""Cliente de la API de Indicadores de INEGI (inegi.org.mx/servicios/
api_indicadores.html) -- primera fuente oficial externa que DiagMuni consulta
en vivo, en vez de depender solo de captura manual del funcionario (ver nota
de arquitectura "De Municipio a Tres Órdenes").

Patrón de URL documentado por INEGI:
  https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/
  INDICATOR/{IdIndicador}/{Idioma}/{ÁreaGeográfica}/{Recientes}/{Fuente}/
  {Versión}/{Token}?type=json

VERIFICADO EN VIVO (2026-09-10, token real, clave_geoestadistica "09004" =
Cuajimalpa de Morelos): el indicador `1002000001` sí es "Población total", y
devuelve una serie histórica completa (1995-2020), no un valor único. El
2020 (217,686) coincide exactamente con el censo oficial. PERO la API
devuelve las observaciones en orden **descendente** por año (2020 primero,
1995 al final) -- lo contrario de lo que este módulo asumía al escribirse sin
poder probarlo ("la última observación es la más reciente"). Ese supuesto
era falso y se corrigió: ahora se elige explícitamente el `TIME_PERIOD` más
alto, sin depender del orden del arreglo.

Cierra de forma segura en cada punto de falla posible (token ausente, HTTP no-200, JSON
con forma inesperada, valor no convertible a entero) -- nunca una excepción
que tumbe el guardado del Perfil del gobierno completo por un problema de un
servicio externo. `None` es la única señal de "no se pudo", sin distinguir la
causa a este nivel (eso vive en los logs de la llamada, no en el valor de
retorno)."""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR"
_TIMEOUT_SEGUNDOS = 10.0


def esta_disponible() -> bool:
    """`False` si no hay token configurado -- la sincronización se deshabilita
    por completo, no falla en cada intento (ver adaptadores/http/gobierno_contexto.py)."""
    return bool(settings.inegi_api_token)


def obtener_poblacion_total(clave_geoestadistica: str) -> int | None:
    """Población total más reciente publicada por INEGI para esa clave
    geoestadística municipal, o `None` si no se pudo obtener por cualquier
    motivo (sin token, sin red, indicador sin datos para esa área, etc.)."""
    if not esta_disponible():
        return None

    url = (
        f"{_BASE_URL}/{settings.inegi_indicador_poblacion_total}/es/"
        f"{clave_geoestadistica}/false/BISE/2.0/{settings.inegi_api_token}"
    )
    try:
        respuesta = httpx.get(url, params={"type": "json"}, timeout=_TIMEOUT_SEGUNDOS)
        respuesta.raise_for_status()
        datos = respuesta.json()
        observaciones = datos["Series"][0]["OBSERVATIONS"]
        if not observaciones:
            return None
        # NO asumir el orden del arreglo (verificado en vivo: INEGI lo devuelve
        # descendente por año, no ascendente) -- se elige explícitamente el
        # TIME_PERIOD más alto.
        mas_reciente = max(observaciones, key=lambda obs: int(obs["TIME_PERIOD"]))
        return int(float(mas_reciente["OBS_VALUE"]))
    except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as error:
        logger.warning(
            "No se pudo obtener población de INEGI para clave_geoestadistica=%s: %s",
            clave_geoestadistica,
            error,
        )
        return None

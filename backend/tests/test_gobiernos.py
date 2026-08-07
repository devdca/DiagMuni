"""Wiring de rate-limiting de GET /api/gobiernos/{clave} -- la lógica genérica
de la ventana deslizante vive en app/core/rate_limit.py y se cubre en
test_rate_limit.py; aquí solo se verifica que este endpoint la configure con
los parámetros documentados (entregables/fase-2/identificacion-gobierno-login.md,
sección 3)."""

from app.api.gobiernos import INTENTOS_MAXIMOS_POR_VENTANA, VENTANA_SEGUNDOS, _limitador
from app.core.rate_limit import LimitadorVentanaDeslizante


def test_limitador_es_una_ventana_deslizante_compartida():
    assert isinstance(_limitador, LimitadorVentanaDeslizante)


def test_limitador_usa_los_parametros_documentados():
    assert INTENTOS_MAXIMOS_POR_VENTANA == 10
    assert VENTANA_SEGUNDOS == 60.0
    assert _limitador.intentos_maximos == INTENTOS_MAXIMOS_POR_VENTANA
    assert _limitador.ventana_segundos == VENTANA_SEGUNDOS

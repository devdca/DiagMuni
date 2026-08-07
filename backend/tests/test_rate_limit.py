"""Tests de app/core/rate_limit.py -- puros, sin dependencia de base de datos.
Antes vivían en test_gobiernos.py (la lógica era propia de ese módulo); se
movieron aquí cuando el limitador se compartió con /api/auth/login (hallazgo de
Strix vuln-0001, "Missing brute-force protection on /api/auth/login")."""

from starlette.requests import Request

from app.core.rate_limit import LimitadorVentanaDeslizante, ip_cliente


def _hacer_request(headers: dict[str, str] | None = None, client_host: str | None = "127.0.0.1") -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": (client_host, 12345) if client_host else None,
    }
    return Request(scope)


def test_ip_cliente_usa_x_real_ip_si_nginx_lo_fijo():
    request = _hacer_request(headers={"x-real-ip": "10.0.0.5"}, client_host="172.18.0.3")
    assert ip_cliente(request) == "10.0.0.5"


def test_ip_cliente_cae_al_remitente_directo_sin_proxy():
    request = _hacer_request(client_host="203.0.113.7")
    assert ip_cliente(request) == "203.0.113.7"


def test_ip_cliente_desconocido_si_no_hay_client_en_el_scope():
    request = _hacer_request(client_host=None)
    assert ip_cliente(request) == "desconocido"


def test_permitir_intento_dentro_del_limite():
    limitador = LimitadorVentanaDeslizante(intentos_maximos=10, ventana_segundos=60.0)
    ip = "198.51.100.1"
    for _ in range(10):
        assert limitador.permitir_intento(ip, ahora=0.0)


def test_permitir_intento_bloquea_al_superar_el_limite():
    limitador = LimitadorVentanaDeslizante(intentos_maximos=10, ventana_segundos=60.0)
    ip = "198.51.100.2"
    for _ in range(10):
        assert limitador.permitir_intento(ip, ahora=0.0)
    assert not limitador.permitir_intento(ip, ahora=0.5)


def test_permitir_intento_libera_cupo_fuera_de_la_ventana():
    limitador = LimitadorVentanaDeslizante(intentos_maximos=10, ventana_segundos=60.0)
    ip = "198.51.100.3"
    for _ in range(10):
        assert limitador.permitir_intento(ip, ahora=0.0)
    assert not limitador.permitir_intento(ip, ahora=1.0)
    # Un segundo más allá de la ventana: el primer intento (t=0.0) ya salió.
    assert limitador.permitir_intento(ip, ahora=61.0)


def test_permitir_intento_claves_distintas_no_comparten_cupo():
    limitador = LimitadorVentanaDeslizante(intentos_maximos=10, ventana_segundos=60.0)
    for _ in range(10):
        assert limitador.permitir_intento("198.51.100.4", ahora=0.0)
    assert limitador.permitir_intento("198.51.100.5", ahora=0.0)


def test_permitir_intento_limites_independientes_por_instancia():
    """Dos limitadores con parámetros distintos (ej. gobiernos 10/60s vs. login
    5/60s, ver app/api/gobiernos.py y app/api/auth.py) no comparten estado ni
    umbral entre sí -- cada router construye su propia instancia."""
    limitador_laxo = LimitadorVentanaDeslizante(intentos_maximos=10, ventana_segundos=60.0)
    limitador_estricto = LimitadorVentanaDeslizante(intentos_maximos=5, ventana_segundos=60.0)
    ip = "198.51.100.6"

    for _ in range(5):
        assert limitador_estricto.permitir_intento(ip, ahora=0.0)
    assert not limitador_estricto.permitir_intento(ip, ahora=0.0)
    # La misma IP en el limitador laxo, sin relación con el estricto, sigue con cupo.
    assert limitador_laxo.permitir_intento(ip, ahora=0.0)

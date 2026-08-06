"""Tests de la ventana deslizante de rate-limiting de GET /api/gobiernos/{clave}
(entregables/fase-2/identificacion-gobierno-login.md, sección 3) -- pura salvo el
registro inyectable, sin depender de una base de datos real."""

from collections import defaultdict, deque

from starlette.requests import Request

from app.api.gobiernos import INTENTOS_MAXIMOS_POR_VENTANA, VENTANA_SEGUNDOS, _ip_cliente, _permitir_intento


def _nuevo_registro() -> dict[str, deque[float]]:
    return defaultdict(deque)


def _hacer_request(headers: dict[str, str] | None = None, client_host: str | None = "127.0.0.1") -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": (client_host, 12345) if client_host else None,
    }
    return Request(scope)


def test_ip_cliente_usa_x_real_ip_si_nginx_lo_fijo():
    request = _hacer_request(headers={"x-real-ip": "10.0.0.5"}, client_host="172.18.0.3")
    assert _ip_cliente(request) == "10.0.0.5"


def test_ip_cliente_cae_al_remitente_directo_sin_proxy():
    request = _hacer_request(client_host="203.0.113.7")
    assert _ip_cliente(request) == "203.0.113.7"


def test_ip_cliente_desconocido_si_no_hay_client_en_el_scope():
    request = _hacer_request(client_host=None)
    assert _ip_cliente(request) == "desconocido"


def test_permitir_intento_dentro_del_limite():
    registro = _nuevo_registro()
    ip = "198.51.100.1"
    for _ in range(INTENTOS_MAXIMOS_POR_VENTANA):
        assert _permitir_intento(ip, ahora=0.0, registro=registro)


def test_permitir_intento_bloquea_al_superar_el_limite():
    registro = _nuevo_registro()
    ip = "198.51.100.2"
    for _ in range(INTENTOS_MAXIMOS_POR_VENTANA):
        assert _permitir_intento(ip, ahora=0.0, registro=registro)
    assert not _permitir_intento(ip, ahora=0.5, registro=registro)


def test_permitir_intento_libera_cupo_fuera_de_la_ventana():
    registro = _nuevo_registro()
    ip = "198.51.100.3"
    for _ in range(INTENTOS_MAXIMOS_POR_VENTANA):
        assert _permitir_intento(ip, ahora=0.0, registro=registro)
    assert not _permitir_intento(ip, ahora=1.0, registro=registro)
    # Un segundo más allá de la ventana: el primer intento (t=0.0) ya salió.
    assert _permitir_intento(ip, ahora=VENTANA_SEGUNDOS + 1.0, registro=registro)


def test_permitir_intento_ips_distintas_no_comparten_cupo():
    registro = _nuevo_registro()
    for _ in range(INTENTOS_MAXIMOS_POR_VENTANA):
        assert _permitir_intento("198.51.100.4", ahora=0.0, registro=registro)
    assert _permitir_intento("198.51.100.5", ahora=0.0, registro=registro)

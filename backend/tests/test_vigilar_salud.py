"""Tests de scripts/vigilar_salud.py -- sin red real, `httpx.get`/`httpx.post`
mockeados. Cubre: no truena sin ALERTA_WEBHOOK_URL, alerta tras M fallos
consecutivos (no antes), y no reinunda el webhook mientras la caída continúa."""

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.vigilar_salud import vigilar  # noqa: E402


class _RespuestaFalsa:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def test_no_truena_sin_webhook_configurado_aunque_todo_falle(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("rechazado")))
    llamadas_post = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: llamadas_post.append((a, k)))

    vigilar(
        url="http://localhost:8090/health",
        intervalo_segundos=0,
        fallos_consecutivos_para_alertar=3,
        webhook_url=None,
        max_iteraciones=5,
    )

    assert llamadas_post == []


def test_no_alerta_antes_de_alcanzar_el_umbral(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("rechazado")))
    llamadas_post = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: llamadas_post.append((a, k)))

    vigilar(
        url="http://localhost:8090/health",
        intervalo_segundos=0,
        fallos_consecutivos_para_alertar=3,
        webhook_url="https://hooks.example/webhook",
        max_iteraciones=2,
    )

    assert llamadas_post == []


def test_alerta_al_alcanzar_m_fallos_consecutivos(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("rechazado")))
    llamadas_post = []
    monkeypatch.setattr(httpx, "post", lambda url, **k: llamadas_post.append((url, k)))

    vigilar(
        url="http://localhost:8090/health",
        intervalo_segundos=0,
        fallos_consecutivos_para_alertar=3,
        webhook_url="https://hooks.example/webhook",
        max_iteraciones=3,
    )

    assert len(llamadas_post) == 1
    url, kwargs = llamadas_post[0]
    assert url == "https://hooks.example/webhook"
    assert "3 chequeos seguidos" in kwargs["json"]["text"]


def test_no_reenvia_alerta_mientras_la_caida_continua(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("rechazado")))
    llamadas_post = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: llamadas_post.append((a, k)))

    vigilar(
        url="http://localhost:8090/health",
        intervalo_segundos=0,
        fallos_consecutivos_para_alertar=3,
        webhook_url="https://hooks.example/webhook",
        max_iteraciones=6,
    )

    assert len(llamadas_post) == 1


def test_recupera_sin_alertar_de_nuevo_tras_un_exito(monkeypatch):
    respuestas = iter(
        [
            httpx.ConnectError("rechazado"),
            httpx.ConnectError("rechazado"),
            httpx.ConnectError("rechazado"),
            _RespuestaFalsa(200),
            httpx.ConnectError("rechazado"),
            httpx.ConnectError("rechazado"),
        ]
    )

    def _get_falso(*_a, **_k):
        resultado = next(respuestas)
        if isinstance(resultado, Exception):
            raise resultado
        return resultado

    monkeypatch.setattr(httpx, "get", _get_falso)
    llamadas_post = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: llamadas_post.append((a, k)))

    vigilar(
        url="http://localhost:8090/health",
        intervalo_segundos=0,
        fallos_consecutivos_para_alertar=3,
        webhook_url="https://hooks.example/webhook",
        max_iteraciones=6,
    )

    # 3 fallos -> alerta; recupera al 4to chequeo; solo 2 fallos más -- no vuelve
    # a alcanzar el umbral, así que no debe haber una segunda alerta.
    assert len(llamadas_post) == 1


def test_status_code_distinto_de_200_cuenta_como_fallo(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _RespuestaFalsa(503))
    llamadas_post = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: llamadas_post.append((a, k)))

    vigilar(
        url="http://localhost:8090/health",
        intervalo_segundos=0,
        fallos_consecutivos_para_alertar=2,
        webhook_url="https://hooks.example/webhook",
        max_iteraciones=2,
    )

    assert len(llamadas_post) == 1


def test_un_error_al_mandar_el_webhook_no_truena_el_script(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("rechazado")))
    monkeypatch.setattr(
        httpx, "post", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("webhook caído también"))
    )

    vigilar(
        url="http://localhost:8090/health",
        intervalo_segundos=0,
        fallos_consecutivos_para_alertar=1,
        webhook_url="https://hooks.example/webhook",
        max_iteraciones=2,
    )


@pytest.mark.parametrize("status_code", [200])
def test_todo_ok_nunca_alerta(monkeypatch, status_code):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _RespuestaFalsa(status_code))
    llamadas_post = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: llamadas_post.append((a, k)))

    vigilar(
        url="http://localhost:8090/health",
        intervalo_segundos=0,
        fallos_consecutivos_para_alertar=1,
        webhook_url="https://hooks.example/webhook",
        max_iteraciones=5,
    )

    assert llamadas_post == []

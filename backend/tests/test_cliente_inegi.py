"""Tests del cliente de INEGI (app/adaptadores/inegi/cliente_inegi.py) --
`httpx.get` mockeado, nunca una llamada de red real (ver advertencia en el
propio módulo: no hay token registrado para probarlo en vivo). El contrato que
importa es que cierre de forma segura ante cualquier falla: cualquier falla
posible devuelve `None`, nunca lanza."""

from typing import Any

import httpx
import pytest

from app.adaptadores.inegi import cliente_inegi
from app.core.config import Settings


def _settings(token: str | None = "token-de-prueba") -> Settings:
    return Settings(inegi_api_token=token)


def test_esta_disponible_es_false_sin_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cliente_inegi, "settings", _settings(None))
    assert cliente_inegi.esta_disponible() is False


def test_esta_disponible_es_true_con_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cliente_inegi, "settings", _settings("abc123"))
    assert cliente_inegi.esta_disponible() is True


def test_obtener_poblacion_total_sin_token_devuelve_none_sin_llamar_red(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cliente_inegi, "settings", _settings(None))

    def _get_no_debe_llamarse(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("No debe llamar a la red sin token configurado.")

    monkeypatch.setattr(httpx, "get", _get_no_debe_llamarse)
    assert cliente_inegi.obtener_poblacion_total("09004") is None


class _RespuestaFalsa:
    def __init__(self, cuerpo: dict[str, Any], status_code: int = 200) -> None:
        self._cuerpo = cuerpo
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=httpx.Request("GET", "https://x"), response=None)  # type: ignore[arg-type]

    def json(self) -> dict[str, Any]:
        return self._cuerpo


def test_obtener_poblacion_total_elige_el_time_period_mas_alto_orden_ascendente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cliente_inegi, "settings", _settings("abc123"))
    cuerpo = {
        "Series": [
            {
                "OBSERVATIONS": [
                    {"TIME_PERIOD": "2010", "OBS_VALUE": "199224"},
                    {"TIME_PERIOD": "2020", "OBS_VALUE": "217686"},
                ]
            }
        ]
    }
    monkeypatch.setattr(httpx, "get", lambda *_a, **_k: _RespuestaFalsa(cuerpo))

    assert cliente_inegi.obtener_poblacion_total("09004") == 217686


def test_obtener_poblacion_total_elige_el_time_period_mas_alto_orden_descendente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regresión directa de un bug real: verificado en vivo (2026-09-10, clave
    09004) que INEGI devuelve las observaciones en orden DESCENDENTE por año
    (más reciente primero) -- la versión anterior de este código asumía
    ascendente y tomaba `observaciones[-1]`, devolviendo 1995 (136873) en vez
    de 2020 (217686) para Cuajimalpa de Morelos."""
    monkeypatch.setattr(cliente_inegi, "settings", _settings("abc123"))
    cuerpo = {
        "Series": [
            {
                "OBSERVATIONS": [
                    {"TIME_PERIOD": "2020", "OBS_VALUE": "217686.00000000000000000000"},
                    {"TIME_PERIOD": "2010", "OBS_VALUE": "186391.00000000000000000000"},
                    {"TIME_PERIOD": "2005", "OBS_VALUE": "173625.00000000000000000000"},
                    {"TIME_PERIOD": "2000", "OBS_VALUE": "151222.00000000000000000000"},
                    {"TIME_PERIOD": "1995", "OBS_VALUE": "136873.00000000000000000000"},
                ]
            }
        ]
    }
    monkeypatch.setattr(httpx, "get", lambda *_a, **_k: _RespuestaFalsa(cuerpo))

    assert cliente_inegi.obtener_poblacion_total("09004") == 217686


def test_obtener_poblacion_total_sin_observaciones_devuelve_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cliente_inegi, "settings", _settings("abc123"))
    monkeypatch.setattr(httpx, "get", lambda *_a, **_k: _RespuestaFalsa({"Series": [{"OBSERVATIONS": []}]}))

    assert cliente_inegi.obtener_poblacion_total("09004") is None


def test_obtener_poblacion_total_json_con_forma_inesperada_devuelve_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cliente_inegi, "settings", _settings("abc123"))
    monkeypatch.setattr(httpx, "get", lambda *_a, **_k: _RespuestaFalsa({"algo_distinto": True}))

    assert cliente_inegi.obtener_poblacion_total("09004") is None


def test_obtener_poblacion_total_error_de_red_devuelve_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cliente_inegi, "settings", _settings("abc123"))

    def _get_falla(*_a: Any, **_k: Any) -> None:
        raise httpx.ConnectError("no hay red")

    monkeypatch.setattr(httpx, "get", _get_falla)
    assert cliente_inegi.obtener_poblacion_total("09004") is None


def test_obtener_poblacion_total_valor_no_numerico_devuelve_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cliente_inegi, "settings", _settings("abc123"))
    cuerpo = {"Series": [{"OBSERVATIONS": [{"OBS_VALUE": "N/D"}]}]}
    monkeypatch.setattr(httpx, "get", lambda *_a, **_k: _RespuestaFalsa(cuerpo))

    assert cliente_inegi.obtener_poblacion_total("09004") is None

"""Tests de app/core/observabilidad.py -- sin red real, `sentry_sdk.init`
mockeado. Cubre el contrato de "sin DSN no pasa nada" y qué códigos HTTP
cuentan como falla para las integraciones de Starlette/FastAPI."""

from unittest.mock import patch

from app.core.observabilidad import CODIGOS_HTTP_COMO_FALLA, inicializar_sentry


def test_sin_dsn_no_inicializa_nada():
    with patch("app.core.observabilidad.sentry_sdk.init") as init_mock:
        resultado = inicializar_sentry(None)

    assert resultado is False
    init_mock.assert_not_called()


def test_dsn_vacio_no_inicializa_nada():
    with patch("app.core.observabilidad.sentry_sdk.init") as init_mock:
        resultado = inicializar_sentry("")

    assert resultado is False
    init_mock.assert_not_called()


def test_con_dsn_inicializa_sentry():
    with patch("app.core.observabilidad.sentry_sdk.init") as init_mock:
        resultado = inicializar_sentry("https://clave@sentry.example/1")

    assert resultado is True
    init_mock.assert_called_once()
    kwargs = init_mock.call_args.kwargs
    assert kwargs["dsn"] == "https://clave@sentry.example/1"


def test_nunca_manda_cuerpo_de_request_ni_pii_por_default():
    with patch("app.core.observabilidad.sentry_sdk.init") as init_mock:
        inicializar_sentry("https://clave@sentry.example/1")

    kwargs = init_mock.call_args.kwargs
    assert kwargs["max_request_body_size"] == "never"
    assert kwargs["send_default_pii"] is False
    assert kwargs["event_scrubber"].recursive is True


def test_solo_5xx_cuenta_como_falla_para_las_integraciones():
    with patch("app.core.observabilidad.sentry_sdk.init") as init_mock:
        inicializar_sentry("https://clave@sentry.example/1")

    integraciones = init_mock.call_args.kwargs["integrations"]
    assert len(integraciones) == 2
    for integracion in integraciones:
        assert 500 in integracion.failed_request_status_codes
        assert 401 not in integracion.failed_request_status_codes
        assert 403 not in integracion.failed_request_status_codes
        assert 404 not in integracion.failed_request_status_codes


def test_codigos_como_falla_es_exactamente_5xx():
    assert CODIGOS_HTTP_COMO_FALLA == frozenset(range(500, 600))
    assert 401 not in CODIGOS_HTTP_COMO_FALLA
    assert 403 not in CODIGOS_HTTP_COMO_FALLA
    assert 404 not in CODIGOS_HTTP_COMO_FALLA

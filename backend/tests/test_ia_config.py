"""Tests de la capa de IA (docs/TRD.md, "Testing"): "tests de que la degradación a
plantilla ocurre correctamente cuando la API no responde o falla -- no se testea la
calidad de la prosa del LLM". E1 no hace ninguna llamada a un LLM todavía, así que
aquí se prueba el equivalente en su alcance: que el YAML cargue correctamente y que
la ausencia (o vacío) de una API key se *detecte* sin lanzar una excepción no
controlada -- la pieza que E2/E3/E4 usarán después para decidir la degradación."""

import pytest

from app.core.config import Settings
from app.ia.config import (
    cargar_model_list,
    esta_disponible,
    obtener_ruta,
)


def _settings_sin_keys() -> Settings:
    return Settings(deepseek_api_key=None, anthropic_api_key=None)


def _settings_con_keys(
    deepseek: str | None = "sk-deepseek-test",
    anthropic: str | None = "sk-anthropic-test",
) -> Settings:
    return Settings(deepseek_api_key=deepseek, anthropic_api_key=anthropic)


def test_yaml_carga_ambas_rutas():
    rutas = cargar_model_list()
    assert set(rutas.keys()) == {"economico", "calidad"}


def test_ruta_economico_es_deepseek():
    ruta = obtener_ruta("economico")
    assert ruta.model == "deepseek/deepseek-chat"
    assert ruta.env_var_api_key == "DEEPSEEK_API_KEY"


def test_ruta_calidad_es_claude():
    ruta = obtener_ruta("calidad")
    assert ruta.model == "anthropic/claude-sonnet-4-5"
    assert ruta.env_var_api_key == "ANTHROPIC_API_KEY"


def test_ruta_inexistente_lanza_keyerror_controlado():
    # Un nombre de ruta que no está en el YAML es un error de configuración real
    # (docs/TRD.md solo define "economico" y "calidad") -- debe fallar fuerte y
    # explícito, no en silencio.
    with pytest.raises(KeyError):
        obtener_ruta("no-existe")


def test_disponible_true_cuando_hay_ambas_keys():
    cfg = _settings_con_keys()
    assert esta_disponible("economico", cfg=cfg) is True
    assert esta_disponible("calidad", cfg=cfg) is True


def test_disponible_false_cuando_falta_una_key_sin_excepcion():
    cfg = _settings_con_keys(deepseek=None, anthropic="sk-anthropic-test")
    # No debe lanzar excepción: la app debe poder preguntar "¿está disponible?" y
    # recibir una respuesta booleana, nunca un traceback.
    assert esta_disponible("economico", cfg=cfg) is False
    assert esta_disponible("calidad", cfg=cfg) is True


def test_disponible_false_cuando_faltan_ambas_keys_sin_excepcion():
    cfg = _settings_sin_keys()
    assert esta_disponible("economico", cfg=cfg) is False
    assert esta_disponible("calidad", cfg=cfg) is False


def test_disponible_false_cuando_key_es_string_vacio():
    # Una variable de entorno definida pero vacía ("") debe tratarse igual que
    # ausente -- un despliegue puede declarar DEEPSEEK_API_KEY= en .env sin valor.
    cfg = _settings_con_keys(deepseek="", anthropic="")
    assert esta_disponible("economico", cfg=cfg) is False
    assert esta_disponible("calidad", cfg=cfg) is False


def test_settings_default_sin_keys_no_rompe():
    # Settings() con los defaults de app/core/config.py (sin .env, como en un
    # arranque limpio sin ninguna key configurada) no debe romper esta_disponible.
    cfg = Settings(deepseek_api_key=None, anthropic_api_key=None, jwt_secret="x")
    assert esta_disponible("economico", cfg=cfg) is False
    assert esta_disponible("calidad", cfg=cfg) is False

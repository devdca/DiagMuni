"""Tests de la config de la capa de IA: que el YAML cargue correctamente y que la
ausencia (o vacío) de una API key se detecte sin lanzar una excepción no
controlada."""

import pytest

from app.core.config import Settings
from app.ia.config import (
    api_base_de,
    cargar_model_list,
    esta_disponible,
    obtener_proveedor_llm,
    obtener_ruta,
    obtener_rutas_generacion,
)


def _settings_sin_keys() -> Settings:
    return Settings(deepseek_api_key=None, anthropic_api_key=None, ollama_api_base=None)


def _settings_con_keys(
    deepseek: str | None = "sk-deepseek-test",
    anthropic: str | None = "sk-anthropic-test",
    ollama_api_base: str | None = None,
) -> Settings:
    return Settings(
        deepseek_api_key=deepseek,
        anthropic_api_key=anthropic,
        ollama_api_base=ollama_api_base,
    )


def test_yaml_carga_todas_las_rutas():
    rutas = cargar_model_list()
    assert set(rutas.keys()) == {"economico", "calidad", "calidad_respaldo", "local"}


def test_ruta_economico_es_deepseek():
    ruta = obtener_ruta("economico")
    assert ruta.model == "deepseek/deepseek-chat"
    assert ruta.env_var_api_key == "DEEPSEEK_API_KEY"


def test_ruta_calidad_es_claude():
    ruta = obtener_ruta("calidad")
    assert ruta.model == "anthropic/claude-sonnet-4-5"
    assert ruta.env_var_api_key == "ANTHROPIC_API_KEY"


def test_ruta_calidad_respaldo_es_claude_fable():
    ruta = obtener_ruta("calidad_respaldo")
    assert ruta.model == "anthropic/claude-fable-5"
    assert ruta.env_var_api_key == "ANTHROPIC_API_KEY"


def test_ruta_local_es_ollama_phi3():
    ruta = obtener_ruta("local")
    assert ruta.model == "ollama/phi3"
    assert ruta.env_var_api_base == "OLLAMA_API_BASE"
    assert ruta.env_var_api_key is None
    assert ruta.timeout_segundos == 180


def test_disponible_local_con_base_ollama():
    cfg = _settings_con_keys(ollama_api_base="http://localhost:11434")
    assert esta_disponible("local", cfg=cfg) is True
    assert api_base_de(obtener_ruta("local"), cfg=cfg) == "http://localhost:11434"


def test_disponible_local_sin_base_ollama():
    cfg = _settings_sin_keys()
    assert esta_disponible("local", cfg=cfg) is False


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


def test_obtener_proveedor_llm_default_es_local():
    cfg = Settings(deepseek_api_key=None, anthropic_api_key=None, ollama_api_base="http://localhost:11434")
    assert obtener_proveedor_llm(cfg) == "local"
    assert obtener_rutas_generacion(cfg) == ["local"]


def test_obtener_proveedor_llm_elige_anthropic_si_disponible():
    cfg = _settings_con_keys(deepseek=None, anthropic="sk-anthropic-test")
    assert obtener_proveedor_llm(cfg) == "anthropic"
    assert obtener_rutas_generacion(cfg) == ["calidad", "calidad_respaldo", "local"]


def test_obtener_proveedor_llm_elige_deepseek_si_disponible_y_anthropic_no():
    cfg = _settings_con_keys(deepseek="sk-deepseek-test", anthropic=None)
    assert obtener_proveedor_llm(cfg) == "deepseek"
    assert obtener_rutas_generacion(cfg) == ["economico", "local"]


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

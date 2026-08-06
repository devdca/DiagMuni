"""Prueba de integración real de la ruta `local` (Ollama/phi3) del generador de
plan (F3) -- sin ningún mock de `litellm.completion`, contra un servidor de Ollama
real. Se salta limpio (skip, no falla) si no hay uno alcanzable con el modelo
`phi3` descargado -- CI no provisiona Ollama, mismo criterio que
`test_api_seguimiento.py` con Postgres real.
"""

import json
import socket
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

import pytest

import app.ia.config as ia_config
from app.core.config import Settings
from app.engine.plantillas import _narrativa_plantilla
from app.engine.reglas_loader import cargar_catalogo
from app.ia import generador_plan

_OLLAMA_API_BASE_PRUEBA = "http://localhost:11434"

_TIMEOUT_MAXIMO_SEGUNDOS = 200  # margen sobre los 180s de timeout de la ruta `local`


def _ollama_real_disponible() -> bool:
    """Chequeo de dos pasos, mismo patrón que `_postgres_real_disponible()` en
    `test_api_seguimiento.py`: primero un `connect` de socket con timeout corto (sin
    esto, apuntar a un host inalcanzable puede colgar la recolección de pytest en
    vez de saltar el test), y luego confirmar que el modelo `phi3` está
    efectivamente descargado -- para no confundir "Ollama no está" con "el modelo
    no está"."""
    url = urlparse(_OLLAMA_API_BASE_PRUEBA)
    try:
        with socket.create_connection((url.hostname or "localhost", url.port or 11434), timeout=2):
            pass
    except OSError:
        return False

    try:
        with urllib.request.urlopen(f"{_OLLAMA_API_BASE_PRUEBA}/api/tags", timeout=2) as respuesta:
            datos = json.load(respuesta)
    except (OSError, urllib.error.URLError, ValueError):
        return False

    modelos = [modelo.get("model", "") for modelo in datos.get("models", [])]
    return any(nombre.startswith("phi3") for nombre in modelos)


@pytest.mark.skipif(
    not _ollama_real_disponible(),
    reason="Requiere Ollama real alcanzable en http://localhost:11434 con el modelo phi3 descargado",
)
def test_generar_contenido_llm_via_ollama_local_real(monkeypatch):
    """Corrida real contra Ollama (litellm.completion sin mockear): genera la
    narrativa de la brecha 'Firma electrónica', la misma acción usada en el
    benchmark original de docs/stack-tecnologico.md, para poder comparar."""
    fake_settings = Settings(
        anthropic_api_key=None,
        deepseek_api_key=None,
        ollama_api_base=_OLLAMA_API_BASE_PRUEBA,
        llm_provider=None,
        jwt_secret="x",
    )
    monkeypatch.setattr(ia_config, "settings_global", fake_settings)

    respuestas = {"firma_electronica_habilitada": False}

    inicio = time.monotonic()
    contenido = generador_plan.generar_contenido_llm(respuestas, "mx")
    duracion = time.monotonic() - inicio

    assert len(contenido["brechas"]) == 1
    brecha = contenido["brechas"][0]
    assert brecha["variable"] == "firma_electronica_habilitada"

    narrativa = brecha["narrativa"].strip()
    assert narrativa != ""

    accion = cargar_catalogo()["firma_electronica_habilitada"].acciones["mx"]
    # Confirma que la narrativa sí vino del LLM real, no que cayó en degradado por
    # un fallo silencioso -- la plantilla determinista es un texto fijo, no generado.
    assert narrativa != _narrativa_plantilla(accion)

    assert duracion < _TIMEOUT_MAXIMO_SEGUNDOS, (
        f"la llamada real tardó {duracion:.1f}s, por encima del margen de "
        f"{_TIMEOUT_MAXIMO_SEGUNDOS}s sobre el timeout de 180s de la ruta local"
    )

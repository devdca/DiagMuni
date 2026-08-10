"""Tests del verificador (F9). Ninguna llamada real a un LLM --
`litellm.completion` siempre monkeypatcheado. Cubre el booleano fail-closed y el
fallback `economico` -> `local` (test_generador_plan_ollama_real.py cubre el caso
sin mocks, contra un Ollama real)."""

from app.ia import verificador
from app.ia.config import obtener_ruta
from app.ia.verificador import verificar_contenido

BRECHA_DETERMINISTA = {
    "variable": "firma_electronica_habilitada",
    "categoria_catalogo": "modulo_firma_electronica",
    "paso_administrativo": "Suscribir convenio de homologación con la e.firma del SAT",
    "paso_tecnico": "Integrar verificación de firma con estándar abierto (PAdES/XAdES)",
    "paso_organizacional": "Capacitar a funcionarios de mostrador en uso del certificado",
    "prerrequisitos": ["conectividad estable"],
    "por_que_importa": "Bloquea el paso de índice 2 a 3 (transaccional completo)",
    "fuente_normativa": "LNETB art. 25; ley estatal + convenio e.firma SAT",
    "narrativa": "narrativa de plantilla, no importa para estos tests",
}

CONTENIDO_DETERMINISTA = {"resumen_narrativo": "x", "brechas": [BRECHA_DETERMINISTA]}


def _brecha_llm(narrativa: str) -> dict:
    return {**BRECHA_DETERMINISTA, "narrativa": narrativa}


def _mock_respuesta(texto: str) -> dict:
    return {"choices": [{"message": {"content": texto}}]}


# --- (a) ninguna ruta de _RUTAS_VERIFICACION disponible -> False, sin llamar ----


def test_ninguna_ruta_disponible_devuelve_false(monkeypatch):
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: False)

    def _completion_no_debe_llamarse(*args, **kwargs):
        raise AssertionError("litellm.completion no debía invocarse sin ninguna ruta disponible")

    monkeypatch.setattr(verificador.litellm, "completion", _completion_no_debe_llamarse)

    contenido_llm = {"resumen_narrativo": "x", "brechas": [_brecha_llm("narrativa fiel")]}
    assert verificar_contenido(contenido_llm, CONTENIDO_DETERMINISTA) is False


# --- (a2) "economico" no disponible pero "local" sí -> usa local, nunca falla cerrado ---


def test_economico_no_disponible_pero_local_si_usa_local(monkeypatch):
    """Regresión del hueco cerrado hoy: antes, sin DEEPSEEK_API_KEY, esto devolvía
    False sin importar que Ollama funcionara -- generador_plan.py quedaba simétrico
    (Claude->Claude respaldo->local->plantilla) pero el auditor no."""
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: ruta == "local")
    # "local" usa api_base, no api_key (ver app/ia/litellm_config.yaml) -- api_key_de
    # debe devolver None para que _veredicto_llm despache api_base, no api_key.
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: None)
    monkeypatch.setattr(verificador, "api_base_de", lambda ruta: "http://ollama:11434")

    llamadas = []

    def _completion_espia(*args, **kwargs):
        llamadas.append(kwargs)
        return _mock_respuesta("SI")

    monkeypatch.setattr(verificador.litellm, "completion", _completion_espia)

    contenido_llm = {"resumen_narrativo": "x", "brechas": [_brecha_llm("narrativa fiel")]}
    assert verificar_contenido(contenido_llm, CONTENIDO_DETERMINISTA) is True

    assert len(llamadas) == 1
    assert llamadas[0]["model"] == "ollama/phi3"
    assert llamadas[0]["api_base"] == "http://ollama:11434"
    assert "api_key" not in llamadas[0]
    assert llamadas[0]["timeout"] == obtener_ruta("local").timeout_segundos


# --- (b) el LLM responde "SI" -> True -------------------------------------------


def test_veredicto_si_aprueba(monkeypatch):
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test")
    monkeypatch.setattr(verificador.litellm, "completion", lambda *a, **k: _mock_respuesta("SI"))

    contenido_llm = {"resumen_narrativo": "x", "brechas": [_brecha_llm("narrativa fiel a los datos")]}
    assert verificar_contenido(contenido_llm, CONTENIDO_DETERMINISTA) is True


# --- (c) el LLM responde "NO" -> False ------------------------------------------


def test_veredicto_no_rechaza(monkeypatch):
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test")
    monkeypatch.setattr(verificador.litellm, "completion", lambda *a, **k: _mock_respuesta("NO"))

    contenido_llm = {
        "resumen_narrativo": "x",
        "brechas": [_brecha_llm("narrativa que inventa una norma que no existe")],
    }
    assert verificar_contenido(contenido_llm, CONTENIDO_DETERMINISTA) is False


# --- (d) la llamada lanza una excepción (timeout, red, etc.) -> False, sin propagar ---


def test_llm_lanza_excepcion_devuelve_false_sin_propagar(monkeypatch):
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test")

    def _completion_falla(*args, **kwargs):
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(verificador.litellm, "completion", _completion_falla)

    contenido_llm = {"resumen_narrativo": "x", "brechas": [_brecha_llm("narrativa fiel")]}
    assert verificar_contenido(contenido_llm, CONTENIDO_DETERMINISTA) is False


# --- (e) respuesta vacía o no parseable -> False (fail-closed, no solo ante error) ----


def test_respuesta_vacia_devuelve_false(monkeypatch):
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test")
    monkeypatch.setattr(verificador.litellm, "completion", lambda *a, **k: _mock_respuesta("   "))

    contenido_llm = {"resumen_narrativo": "x", "brechas": [_brecha_llm("narrativa fiel")]}
    assert verificar_contenido(contenido_llm, CONTENIDO_DETERMINISTA) is False


def test_respuesta_ambigua_no_reconocida_devuelve_false(monkeypatch):
    # Ni "SI" ni "NO" reconocible -- no se asume aprobado por defecto.
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test")
    monkeypatch.setattr(
        verificador.litellm, "completion", lambda *a, **k: _mock_respuesta("Sí, parece razonable.")
    )

    contenido_llm = {"resumen_narrativo": "x", "brechas": [_brecha_llm("narrativa fiel")]}
    assert verificar_contenido(contenido_llm, CONTENIDO_DETERMINISTA) is False


# --- (f) discrepancia estructural: cantidad de brechas no coincide -> False, sin llamar ---


def test_cantidad_de_brechas_no_coincide_devuelve_false_sin_llamar(monkeypatch):
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test")

    def _completion_no_debe_llamarse(*args, **kwargs):
        raise AssertionError("litellm.completion no debía invocarse ante discrepancia estructural")

    monkeypatch.setattr(verificador.litellm, "completion", _completion_no_debe_llamarse)

    contenido_llm = {
        "resumen_narrativo": "x",
        "brechas": [_brecha_llm("narrativa 1"), _brecha_llm("narrativa 2")],
    }
    assert verificar_contenido(contenido_llm, CONTENIDO_DETERMINISTA) is False


# --- (g) variable de la brecha LLM no existe en el determinista -> False -------


def test_variable_sin_contraparte_determinista_devuelve_false(monkeypatch):
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test")
    monkeypatch.setattr(verificador.litellm, "completion", lambda *a, **k: _mock_respuesta("SI"))

    brecha_otra_variable = {**BRECHA_DETERMINISTA, "variable": "otra_variable_no_existe"}
    contenido_llm = {"resumen_narrativo": "x", "brechas": [brecha_otra_variable]}
    assert verificar_contenido(contenido_llm, CONTENIDO_DETERMINISTA) is False


# --- (h) espía: se llama con la ruta/model/api_key correctos --------------------


def test_llm_recibe_model_y_api_key_de_la_ruta_economico(monkeypatch):
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test-economico")

    llamadas = []

    def _completion_espia(*args, **kwargs):
        llamadas.append(kwargs)
        return _mock_respuesta("SI")

    monkeypatch.setattr(verificador.litellm, "completion", _completion_espia)

    contenido_llm = {"resumen_narrativo": "x", "brechas": [_brecha_llm("narrativa fiel")]}
    verificar_contenido(contenido_llm, CONTENIDO_DETERMINISTA)

    assert len(llamadas) == 1
    assert llamadas[0]["model"] == "deepseek/deepseek-chat"
    assert llamadas[0]["api_key"] == "sk-test-economico"
    assert llamadas[0]["timeout"] == obtener_ruta("economico").timeout_segundos


# --- (i) sin brechas en ambos lados -> True (nada que auditar, no hay discrepancia) ---


def test_sin_brechas_en_ambos_lados_devuelve_true_sin_llamar(monkeypatch):
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test")

    def _completion_no_debe_llamarse(*args, **kwargs):
        raise AssertionError("litellm.completion no debía invocarse sin brechas que auditar")

    monkeypatch.setattr(verificador.litellm, "completion", _completion_no_debe_llamarse)

    contenido_vacio = {"resumen_narrativo": "no hay brechas", "brechas": []}
    assert verificar_contenido(contenido_vacio, contenido_vacio) is True

"""Tests del generador de plan con LLM (F3). Ninguno hace una llamada real --
`litellm.completion` siempre monkeypatcheado."""

from app.engine.plantillas import _narrativa_plantilla, generar_contenido_degradado
from app.ia import generador_plan
from app.ia.generador_plan import generar_contenido_llm

RESPUESTAS_SIN_NADA = {
    "documentos_digitalizados": False,
    "motor_pagos": False,
    "firma_electronica_habilitada": False,
    "interoperabilidad": False,
    "proteccion_datos_incompleta": True,
    "mecanismo_identidad": "ninguno",
}

RESPUESTAS_NIVEL_MAXIMO = {
    "documentos_digitalizados": True,
    "motor_pagos": True,
    "firma_electronica_habilitada": True,
    "interoperabilidad": True,
    "proteccion_datos_incompleta": False,
    "mecanismo_identidad": "llave_mx",
}


def _mock_respuesta_llm(texto: str) -> dict:
    """Simula la forma de un `ModelResponse` de LiteLLM (acceso tipo dict), sin
    depender del SDK real ni de ninguna llamada de red."""
    return {"choices": [{"message": {"content": texto}}]}


# --- (a) esta_disponible("calidad") == False -> cae a narrativa de plantilla -----


def test_sin_api_key_cae_a_narrativa_de_plantilla(monkeypatch):
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: False)

    contenido = generar_contenido_llm(RESPUESTAS_SIN_NADA, "mx")
    esperado = generar_contenido_degradado(RESPUESTAS_SIN_NADA, "mx")

    narrativas_llm = {b["variable"]: b["narrativa"] for b in contenido["brechas"]}
    narrativas_degradado = {b["variable"]: b["narrativa"] for b in esperado["brechas"]}
    assert narrativas_llm == narrativas_degradado


def test_sin_api_key_no_intenta_llamar_al_llm(monkeypatch):
    # Si esta_disponible() es False, ni siquiera debe invocarse litellm.completion --
    # ni la ruta `calidad` (Sonnet) ni la de respaldo `calidad_respaldo` (Fable).
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: False)

    def _completion_no_debe_llamarse(*args, **kwargs):
        raise AssertionError("litellm.completion no debía invocarse sin API key")

    monkeypatch.setattr(generador_plan.litellm, "completion", _completion_no_debe_llamarse)

    contenido = generar_contenido_llm(RESPUESTAS_SIN_NADA, "mx")
    assert len(contenido["brechas"]) > 0


# --- (b) el mock del LLM lanza una excepción -> cae a plantilla sin propagar ----


def test_llm_lanza_excepcion_cae_a_plantilla_sin_propagar(monkeypatch):
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test")

    def _completion_falla(*args, **kwargs):
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(generador_plan.litellm, "completion", _completion_falla)

    contenido = generar_contenido_llm(RESPUESTAS_SIN_NADA, "mx")
    esperado = generar_contenido_degradado(RESPUESTAS_SIN_NADA, "mx")

    narrativas_llm = {b["variable"]: b["narrativa"] for b in contenido["brechas"]}
    narrativas_degradado = {b["variable"]: b["narrativa"] for b in esperado["brechas"]}
    assert narrativas_llm == narrativas_degradado


def test_llm_devuelve_respuesta_vacia_cae_a_plantilla(monkeypatch):
    # Respuesta "exitosa" pero con contenido vacío/None también debe degradar --
    # no es una excepción de red, pero tampoco es prosa utilizable.
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test")
    monkeypatch.setattr(
        generador_plan.litellm, "completion", lambda *a, **k: _mock_respuesta_llm("   ")
    )

    contenido = generar_contenido_llm(RESPUESTAS_SIN_NADA, "mx")
    esperado = generar_contenido_degradado(RESPUESTAS_SIN_NADA, "mx")

    narrativas_llm = {b["variable"]: b["narrativa"] for b in contenido["brechas"]}
    narrativas_degradado = {b["variable"]: b["narrativa"] for b in esperado["brechas"]}
    assert narrativas_llm == narrativas_degradado


# --- (b-bis) cadena de respaldo Sonnet -> Fable -> plantilla --------------------


def test_sonnet_falla_fable_responde_usa_prosa_de_fable(monkeypatch):
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test")

    def _completion_espia(*args, **kwargs):
        if kwargs["model"] == "anthropic/claude-sonnet-4-5":
            raise TimeoutError("simulated timeout en Sonnet")
        return _mock_respuesta_llm("Prosa generada por Fable.")

    monkeypatch.setattr(generador_plan.litellm, "completion", _completion_espia)

    contenido = generar_contenido_llm(RESPUESTAS_SIN_NADA, "mx")

    assert len(contenido["brechas"]) > 0
    for brecha in contenido["brechas"]:
        assert brecha["narrativa"] == "Prosa generada por Fable."
        assert brecha["narrativa"] != _narrativa_plantilla(
            _accion_de(brecha["variable"], "mx")
        )


def test_sonnet_y_fable_fallan_cae_a_plantilla_sin_propagar(monkeypatch):
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test")

    def _completion_falla_siempre(*args, **kwargs):
        raise TimeoutError(f"simulated timeout en {kwargs['model']}")

    monkeypatch.setattr(generador_plan.litellm, "completion", _completion_falla_siempre)

    contenido = generar_contenido_llm(RESPUESTAS_SIN_NADA, "mx")
    esperado = generar_contenido_degradado(RESPUESTAS_SIN_NADA, "mx")

    narrativas_llm = {b["variable"]: b["narrativa"] for b in contenido["brechas"]}
    narrativas_degradado = {b["variable"]: b["narrativa"] for b in esperado["brechas"]}
    assert narrativas_llm == narrativas_degradado


def test_sonnet_falla_fable_recibe_model_y_api_key_correctos(monkeypatch):
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test-respaldo")

    llamadas = []

    def _completion_espia(*args, **kwargs):
        llamadas.append(kwargs)
        if kwargs["model"] == "anthropic/claude-sonnet-4-5":
            raise TimeoutError("simulated timeout en Sonnet")
        return _mock_respuesta_llm("prosa de fable")

    monkeypatch.setattr(generador_plan.litellm, "completion", _completion_espia)

    generar_contenido_llm(RESPUESTAS_SIN_NADA, "mx")

    llamadas_fable = [k for k in llamadas if k["model"] == "anthropic/claude-fable-5"]
    assert len(llamadas_fable) > 0
    for kwargs in llamadas_fable:
        assert kwargs["api_key"] == "sk-test-respaldo"
        assert kwargs["timeout"] == generador_plan.TIMEOUT_SEGUNDOS


# --- (c) esta_disponible == True y mock exitoso -> usa la prosa del mock -------


def test_llm_exitoso_usa_prosa_del_mock_no_la_de_plantilla(monkeypatch):
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test")
    monkeypatch.setattr(
        generador_plan.litellm,
        "completion",
        lambda *a, **k: _mock_respuesta_llm("Prosa generada por el mock de Claude."),
    )

    contenido = generar_contenido_llm(RESPUESTAS_SIN_NADA, "mx")

    assert len(contenido["brechas"]) > 0
    for brecha in contenido["brechas"]:
        assert brecha["narrativa"] == "Prosa generada por el mock de Claude."
        # No debe coincidir con la narrativa de plantilla -- confirma que sí se usó el mock.
        assert brecha["narrativa"] != _narrativa_plantilla(
            _accion_de(brecha["variable"], "mx")
        )


def _accion_de(variable: str, pais: str):
    from app.engine.reglas_loader import cargar_catalogo

    return cargar_catalogo()[variable].acciones[pais]


def test_llm_recibe_model_y_api_key_correctos_de_la_ruta_calidad(monkeypatch):
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test-calidad")

    llamadas = []

    def _completion_espia(*args, **kwargs):
        llamadas.append(kwargs)
        return _mock_respuesta_llm("prosa")

    monkeypatch.setattr(generador_plan.litellm, "completion", _completion_espia)

    generar_contenido_llm(RESPUESTAS_SIN_NADA, "mx")

    assert len(llamadas) > 0
    for kwargs in llamadas:
        assert kwargs["model"] == "anthropic/claude-sonnet-4-5"
        assert kwargs["api_key"] == "sk-test-calidad"
        assert kwargs["timeout"] == generador_plan.TIMEOUT_SEGUNDOS


# --- (d) fidelidad de contrato: demás campos idénticos a generar_contenido_degradado ----


def _sin_narrativa_ni_componente_recomendado(brechas: list[dict]) -> list[dict]:
    # `componente_recomendado` (F4/F5) hoy solo lo agrega generar_contenido_degradado;
    # generar_contenido_llm no lo incluye todavía -- asimetría deliberada del wiring,
    # no una regresión de paridad entre ambos modos.
    claves_excluidas = ("narrativa", "componente_recomendado")
    return [{k: v for k, v in b.items() if k not in claves_excluidas} for b in brechas]


def test_demas_campos_identicos_a_generar_contenido_degradado_sin_llm(monkeypatch):
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: False)

    contenido_llm = generar_contenido_llm(RESPUESTAS_SIN_NADA, "mx")
    contenido_degradado = generar_contenido_degradado(RESPUESTAS_SIN_NADA, "mx")

    llm_ordenado = sorted(
        _sin_narrativa_ni_componente_recomendado(contenido_llm["brechas"]), key=lambda b: b["variable"]
    )
    degradado_ordenado = sorted(
        _sin_narrativa_ni_componente_recomendado(contenido_degradado["brechas"]), key=lambda b: b["variable"]
    )
    assert llm_ordenado == degradado_ordenado


def test_demas_campos_identicos_a_generar_contenido_degradado_con_llm_exitoso(monkeypatch):
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test")
    monkeypatch.setattr(
        generador_plan.litellm, "completion", lambda *a, **k: _mock_respuesta_llm("prosa mock")
    )

    contenido_llm = generar_contenido_llm(RESPUESTAS_SIN_NADA, "uy")
    contenido_degradado = generar_contenido_degradado(RESPUESTAS_SIN_NADA, "uy")

    llm_ordenado = sorted(
        _sin_narrativa_ni_componente_recomendado(contenido_llm["brechas"]), key=lambda b: b["variable"]
    )
    degradado_ordenado = sorted(
        _sin_narrativa_ni_componente_recomendado(contenido_degradado["brechas"]), key=lambda b: b["variable"]
    )
    assert llm_ordenado == degradado_ordenado


# --- caso especial: sin brechas no fuerza narrativa (igual que el modo degradado) ----


def test_nivel_maximo_sin_brechas_no_fuerza_recomendacion(monkeypatch):
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)

    def _completion_no_debe_llamarse(*args, **kwargs):
        raise AssertionError("no hay brechas: no debería llamarse al LLM")

    monkeypatch.setattr(generador_plan.litellm, "completion", _completion_no_debe_llamarse)

    contenido = generar_contenido_llm(RESPUESTAS_NIVEL_MAXIMO, "mx")
    assert contenido["brechas"] == []
    assert "no hay" in contenido["resumen_narrativo"].lower()


def test_resumen_narrativo_es_deterministico_no_via_llm(monkeypatch):
    # Decisión de diseño documentada en generador_plan.py: el resumen de nivel de
    # plan nunca pasa por el LLM. Aunque esta_disponible() sea True y haya un mock
    # de completion configurado, el resumen debe ser idéntico al del modo degradado.
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test")
    monkeypatch.setattr(
        generador_plan.litellm, "completion", lambda *a, **k: _mock_respuesta_llm("prosa mock")
    )

    contenido_llm = generar_contenido_llm(RESPUESTAS_SIN_NADA, "mx")
    contenido_degradado = generar_contenido_degradado(RESPUESTAS_SIN_NADA, "mx")
    assert contenido_llm["resumen_narrativo"] == contenido_degradado["resumen_narrativo"]

"""Tests de `_generar_contenido_y_modo`, la función pura de `app/jobs/plan_job.py`
que decide qué contenido y modo persiste `ejecutar_generacion_plan`.

No requieren base de datos real -- eso no se toca ni se testea acá. Se mockea
`litellm.completion`, nunca red real. Son tests de integración entre `plan_job`,
`generador_plan` y `verificador` (mockeando solo en el límite de red/config), no
`verificar_contenido` -- así se ejercita la cadena real de decisión, no una
simulación de su resultado.

Nota técnica: `generador_plan` y `verificador` hacen `import litellm` por separado,
pero es el mismo objeto módulo en el proceso -- `generador_plan.litellm is
verificador.litellm`. Por eso el mock de `completion` es UNA sola función que
distingue la llamada de redacción (E2) de la de auditoría (E3) inspeccionando el
prompt, en vez de dos `monkeypatch.setattr` independientes que se pisarían entre sí.
"""

from app.engine.plantillas import generar_contenido_degradado
from app.ia import generador_plan, verificador
from app.jobs import plan_job

RESPUESTAS_CON_BRECHAS = {
    "documentos_digitalizados": False,
    "motor_pagos": False,
    "firma_electronica_habilitada": False,
    "interoperabilidad": False,
    "proteccion_datos_incompleta": True,
    "mecanismo_identidad": "ninguno",
}


def _mock_respuesta(texto: str) -> dict:
    return {"choices": [{"message": {"content": texto}}]}


def _mockear_generacion_exitosa(monkeypatch, narrativa: str = "prosa redactada por el mock de Claude") -> None:
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test-calidad")
    monkeypatch.setattr(generador_plan.litellm, "completion", lambda *a, **k: _mock_respuesta(narrativa))


def _mockear_completion_combinado(monkeypatch, narrativa: str, veredicto: str) -> None:
    """Un solo mock de `litellm.completion` (mismo objeto módulo en `generador_plan`
    y en `verificador`, ver nota del módulo) que responde `narrativa` a la llamada
    de redacción (E2) y `veredicto` a la llamada de auditoría (E3), distinguiéndolas
    por el prompt -- el prompt de `verificador.py` pide explícitamente "SI"/"NO"."""

    def _completion(*args, **kwargs):
        prompt = kwargs["messages"][0]["content"]
        if "auditor de fidelidad" in prompt:
            return _mock_respuesta(veredicto)
        return _mock_respuesta(narrativa)

    monkeypatch.setattr(generador_plan.litellm, "completion", _completion)


# --- (a) ruta "calidad" no disponible -> degradado, SIN llamar nunca al verificador ---


def test_calidad_no_disponible_va_directo_a_degradado_sin_llamar_verificador(monkeypatch):
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: False)

    def _verificar_no_debe_llamarse(*args, **kwargs):
        raise AssertionError("verificar_contenido no debía invocarse sin ruta 'calidad' disponible")

    monkeypatch.setattr(plan_job, "verificar_contenido", _verificar_no_debe_llamarse)

    def _generar_llm_no_debe_llamarse(*args, **kwargs):
        raise AssertionError("generar_contenido_llm no debía invocarse sin ruta 'calidad' disponible")

    monkeypatch.setattr(plan_job, "generar_contenido_llm", _generar_llm_no_debe_llamarse)

    modo, contenido, verificado = plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx")

    assert modo == "degradado"
    assert verificado is True
    assert contenido == generar_contenido_degradado(RESPUESTAS_CON_BRECHAS, "mx")


# --- (b) verificación exitosa -> modo llm, verificado=True ----------------------


def test_verificacion_exitosa_persiste_modo_llm(monkeypatch):
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test-calidad")
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test-economico")
    _mockear_completion_combinado(
        monkeypatch, narrativa="prosa redactada por el mock de Claude", veredicto="SI"
    )

    modo, contenido, verificado = plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx")

    assert modo == "llm"
    assert verificado is True
    assert len(contenido["brechas"]) > 0
    for brecha in contenido["brechas"]:
        assert brecha["narrativa"] == "prosa redactada por el mock de Claude"


# --- (c) verificación fallida (el auditor responde NO) -> degradado, verificado=True ---


def test_verificacion_fallida_cae_a_degradado(monkeypatch):
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test-calidad")
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test-economico")
    _mockear_completion_combinado(
        monkeypatch, narrativa="prosa redactada por el mock de Claude", veredicto="NO"
    )

    modo, contenido, verificado = plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx")

    assert modo == "degradado"
    assert verificado is True
    assert contenido == generar_contenido_degradado(RESPUESTAS_CON_BRECHAS, "mx")


# --- (d) verificador no disponible (sin key para "economico") -> degradado, verificado=True ---


def test_verificador_no_disponible_cae_a_degradado(monkeypatch):
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: True)
    _mockear_generacion_exitosa(monkeypatch)

    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: False)

    llamadas_auditoria = []

    def _completion_espia(*args, **kwargs):
        prompt = kwargs["messages"][0]["content"]
        if "auditor de fidelidad" in prompt:
            llamadas_auditoria.append(kwargs)
        return _mock_respuesta("prosa redactada por el mock de Claude")

    monkeypatch.setattr(verificador.litellm, "completion", _completion_espia)

    modo, contenido, verificado = plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx")

    assert llamadas_auditoria == []  # el verificador nunca intentó auditar
    assert modo == "degradado"
    assert verificado is True
    assert contenido == generar_contenido_degradado(RESPUESTAS_CON_BRECHAS, "mx")


# --- (e) el verificador lanza una excepción (timeout/red) -> degradado, verificado=True ---


def test_verificador_lanza_excepcion_cae_a_degradado(monkeypatch):
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test-calidad")
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test-economico")

    def _completion(*args, **kwargs):
        prompt = kwargs["messages"][0]["content"]
        if "auditor de fidelidad" in prompt:
            raise TimeoutError("simulated timeout")
        return _mock_respuesta("prosa redactada por el mock de Claude")

    monkeypatch.setattr(generador_plan.litellm, "completion", _completion)

    modo, contenido, verificado = plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx")

    assert modo == "degradado"
    assert verificado is True
    assert contenido == generar_contenido_degradado(RESPUESTAS_CON_BRECHAS, "mx")


# --- (f) nunca se produce verificado=False en ningún camino ---------------------


def test_verificado_nunca_es_false(monkeypatch):
    escenarios = []

    # calidad no disponible
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: False)
    escenarios.append(plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx"))

    # calidad disponible, verificador aprueba
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test")
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test")
    _mockear_completion_combinado(monkeypatch, narrativa="prosa mock", veredicto="SI")
    escenarios.append(plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx"))

    # calidad disponible, verificador rechaza
    _mockear_completion_combinado(monkeypatch, narrativa="prosa mock", veredicto="NO")
    escenarios.append(plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx"))

    for _modo, _contenido, verificado in escenarios:
        assert verificado is True

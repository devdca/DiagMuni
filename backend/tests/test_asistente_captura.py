"""Tests del asistente de captura F1. Ninguna llamada real a un LLM --
`litellm.completion` siempre monkeypatcheado. Cubre el sesgo fail-safe: cualquier
fallo cae en `no_concluyente`/`no_clasificable`, nunca en una excepción propagada."""

from app.ia import asistente_captura
from app.ia.asistente_captura import (
    ID_URUGUAY,
    LLAVE_MX,
    NINGUNO,
    NO_CLASIFICABLE,
    NO_CONCLUYENTE,
    POSIBLE_CONTRADICCION_HACIA_NO,
    POSIBLE_CONTRADICCION_HACIA_SI,
    PROPIO,
    clasificar_consistencia_booleana,
    clasificar_mecanismo_identidad,
)


def _mock_respuesta(texto: str) -> dict:
    return {"choices": [{"message": {"content": texto}}]}


def _disponible(monkeypatch, disponible: bool = True) -> None:
    monkeypatch.setattr(asistente_captura, "esta_disponible", lambda ruta: disponible)
    monkeypatch.setattr(asistente_captura, "api_key_de", lambda ruta: "sk-test")


# === (A) clasificar_consistencia_booleana ========================================

# --- 4 categorías exitosas --------------------------------------------------------


def test_consistencia_devuelve_consistente(monkeypatch):
    _disponible(monkeypatch)
    monkeypatch.setattr(
        asistente_captura.litellm, "completion", lambda *a, **k: _mock_respuesta("consistente")
    )
    resultado = clasificar_consistencia_booleana("todo normal, sin novedad", valor_marcado=True)
    assert resultado == "consistente"


def test_consistencia_devuelve_posible_contradiccion_hacia_si(monkeypatch):
    _disponible(monkeypatch)
    monkeypatch.setattr(
        asistente_captura.litellm,
        "completion",
        lambda *a, **k: _mock_respuesta("posible_contradiccion_hacia_si"),
    )
    resultado = clasificar_consistencia_booleana(
        "marcamos No, pero usamos firma digital para todos los documentos desde 2024",
        valor_marcado=False,
    )
    assert resultado == POSIBLE_CONTRADICCION_HACIA_SI


def test_consistencia_devuelve_posible_contradiccion_hacia_no(monkeypatch):
    _disponible(monkeypatch)
    monkeypatch.setattr(
        asistente_captura.litellm,
        "completion",
        lambda *a, **k: _mock_respuesta("posible_contradiccion_hacia_no"),
    )
    resultado = clasificar_consistencia_booleana(
        "marcamos Sí, pero en realidad solo aceptamos depósito bancario sin conciliación",
        valor_marcado=True,
    )
    assert resultado == POSIBLE_CONTRADICCION_HACIA_NO


def test_consistencia_devuelve_no_concluyente_por_respuesta_del_llm(monkeypatch):
    _disponible(monkeypatch)
    monkeypatch.setattr(
        asistente_captura.litellm, "completion", lambda *a, **k: _mock_respuesta("no_concluyente")
    )
    resultado = clasificar_consistencia_booleana("texto ambiguo, no queda claro", valor_marcado=True)
    assert resultado == NO_CONCLUYENTE


# --- fail-safe: ruta no disponible ------------------------------------------------


def test_consistencia_ruta_no_disponible_devuelve_no_concluyente_sin_llamar(monkeypatch):
    monkeypatch.setattr(asistente_captura, "esta_disponible", lambda ruta: False)

    def _completion_no_debe_llamarse(*args, **kwargs):
        raise AssertionError("litellm.completion no debía invocarse sin ruta 'economico' disponible")

    monkeypatch.setattr(asistente_captura.litellm, "completion", _completion_no_debe_llamarse)

    resultado = clasificar_consistencia_booleana("cualquier texto", valor_marcado=True)
    assert resultado == NO_CONCLUYENTE


# --- fail-safe: excepción (timeout, red, etc.) ------------------------------------


def test_consistencia_excepcion_devuelve_no_concluyente_sin_propagar(monkeypatch):
    _disponible(monkeypatch)

    def _completion_falla(*args, **kwargs):
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(asistente_captura.litellm, "completion", _completion_falla)

    resultado = clasificar_consistencia_booleana("cualquier texto", valor_marcado=True)
    assert resultado == NO_CONCLUYENTE


# --- fail-safe: respuesta no reconocible / vacía ----------------------------------


def test_consistencia_respuesta_no_reconocible_devuelve_no_concluyente(monkeypatch):
    _disponible(monkeypatch)
    monkeypatch.setattr(
        asistente_captura.litellm,
        "completion",
        lambda *a, **k: _mock_respuesta("esto no es ninguna de las categorías esperadas"),
    )
    resultado = clasificar_consistencia_booleana("cualquier texto", valor_marcado=True)
    assert resultado == NO_CONCLUYENTE


def test_consistencia_respuesta_vacia_devuelve_no_concluyente(monkeypatch):
    _disponible(monkeypatch)
    monkeypatch.setattr(asistente_captura.litellm, "completion", lambda *a, **k: _mock_respuesta("   "))
    resultado = clasificar_consistencia_booleana("cualquier texto", valor_marcado=True)
    assert resultado == NO_CONCLUYENTE


# --- espía: model/api_key/timeout correctos ---------------------------------------


def test_consistencia_llm_recibe_model_api_key_y_timeout_correctos(monkeypatch):
    _disponible(monkeypatch)

    llamadas = []

    def _completion_espia(*args, **kwargs):
        llamadas.append(kwargs)
        return _mock_respuesta("consistente")

    monkeypatch.setattr(asistente_captura.litellm, "completion", _completion_espia)

    clasificar_consistencia_booleana("cualquier texto", valor_marcado=True)

    assert len(llamadas) == 1
    assert llamadas[0]["model"] == "deepseek/deepseek-v4-pro"
    assert llamadas[0]["api_key"] == "sk-test"
    assert llamadas[0]["timeout"] == asistente_captura.TIMEOUT_SEGUNDOS
    assert llamadas[0]["extra_body"] == {"thinking": {"type": "disabled"}}


# === (B) clasificar_mecanismo_identidad ==========================================

# --- 5 categorías exitosas ---------------------------------------------------------


def test_mecanismo_identidad_llave_mx_para_pais_mx(monkeypatch):
    _disponible(monkeypatch)
    monkeypatch.setattr(
        asistente_captura.litellm, "completion", lambda *a, **k: _mock_respuesta("llave_mx")
    )
    resultado = clasificar_mecanismo_identidad("usamos la llave nacional mexicana", pais="mx")
    assert resultado == LLAVE_MX


def test_mecanismo_identidad_id_uruguay_para_pais_uy(monkeypatch):
    _disponible(monkeypatch)
    monkeypatch.setattr(
        asistente_captura.litellm, "completion", lambda *a, **k: _mock_respuesta("id_uruguay")
    )
    resultado = clasificar_mecanismo_identidad("usamos la cédula/ID Uruguay nacional", pais="uy")
    assert resultado == ID_URUGUAY


def test_mecanismo_identidad_propio(monkeypatch):
    _disponible(monkeypatch)
    monkeypatch.setattr(asistente_captura.litellm, "completion", lambda *a, **k: _mock_respuesta("propio"))
    resultado = clasificar_mecanismo_identidad(
        "tenemos una cédula digital propia de la intendencia, no es un mecanismo nacional",
        pais="uy",
    )
    assert resultado == PROPIO


def test_mecanismo_identidad_ninguno(monkeypatch):
    _disponible(monkeypatch)
    monkeypatch.setattr(asistente_captura.litellm, "completion", lambda *a, **k: _mock_respuesta("ninguno"))
    resultado = clasificar_mecanismo_identidad("no tenemos ningún mecanismo de identidad", pais="mx")
    assert resultado == NINGUNO


def test_mecanismo_identidad_no_clasificable_por_respuesta_del_llm(monkeypatch):
    _disponible(monkeypatch)
    monkeypatch.setattr(
        asistente_captura.litellm, "completion", lambda *a, **k: _mock_respuesta("no_clasificable")
    )
    resultado = clasificar_mecanismo_identidad("texto totalmente ambiguo", pais="mx")
    assert resultado == NO_CLASIFICABLE


# --- restricción de candidatas por país (doble barrera) ---------------------------


def test_mecanismo_identidad_prompt_no_ofrece_id_uruguay_para_pais_mx(monkeypatch):
    _disponible(monkeypatch)

    prompts = []

    def _completion_espia(*args, **kwargs):
        prompts.append(kwargs["messages"][0]["content"])
        return _mock_respuesta("propio")

    monkeypatch.setattr(asistente_captura.litellm, "completion", _completion_espia)

    clasificar_mecanismo_identidad("texto cualquiera", pais="mx")

    assert len(prompts) == 1
    assert "id_uruguay" not in prompts[0].lower()
    assert "llave_mx" in prompts[0].lower()


def test_mecanismo_identidad_prompt_no_ofrece_llave_mx_para_pais_uy(monkeypatch):
    _disponible(monkeypatch)

    prompts = []

    def _completion_espia(*args, **kwargs):
        prompts.append(kwargs["messages"][0]["content"])
        return _mock_respuesta("propio")

    monkeypatch.setattr(asistente_captura.litellm, "completion", _completion_espia)

    clasificar_mecanismo_identidad("texto cualquiera", pais="uy")

    assert len(prompts) == 1
    assert "llave_mx" not in prompts[0].lower()
    assert "id_uruguay" in prompts[0].lower()


def test_mecanismo_identidad_invalida_id_uruguay_devuelto_para_pais_mx(monkeypatch):
    # El LLM devuelve, por error, la categoría del país contrario -- el código debe
    # tratarla como no válida y caer a `no_clasificable`, nunca dejarla pasar.
    _disponible(monkeypatch)
    monkeypatch.setattr(
        asistente_captura.litellm, "completion", lambda *a, **k: _mock_respuesta("id_uruguay")
    )
    resultado = clasificar_mecanismo_identidad("texto cualquiera", pais="mx")
    assert resultado == NO_CLASIFICABLE
    assert resultado != ID_URUGUAY


def test_mecanismo_identidad_invalida_llave_mx_devuelto_para_pais_uy(monkeypatch):
    # Mismo caso, en sentido inverso.
    _disponible(monkeypatch)
    monkeypatch.setattr(
        asistente_captura.litellm, "completion", lambda *a, **k: _mock_respuesta("llave_mx")
    )
    resultado = clasificar_mecanismo_identidad("texto cualquiera", pais="uy")
    assert resultado == NO_CLASIFICABLE
    assert resultado != LLAVE_MX


# --- fail-safe: ruta no disponible ------------------------------------------------


def test_mecanismo_identidad_ruta_no_disponible_devuelve_no_clasificable_sin_llamar(monkeypatch):
    monkeypatch.setattr(asistente_captura, "esta_disponible", lambda ruta: False)

    def _completion_no_debe_llamarse(*args, **kwargs):
        raise AssertionError("litellm.completion no debía invocarse sin ruta 'economico' disponible")

    monkeypatch.setattr(asistente_captura.litellm, "completion", _completion_no_debe_llamarse)

    resultado = clasificar_mecanismo_identidad("cualquier texto", pais="mx")
    assert resultado == NO_CLASIFICABLE


# --- fail-safe: excepción (timeout, red, etc.) ------------------------------------


def test_mecanismo_identidad_excepcion_devuelve_no_clasificable_sin_propagar(monkeypatch):
    _disponible(monkeypatch)

    def _completion_falla(*args, **kwargs):
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(asistente_captura.litellm, "completion", _completion_falla)

    resultado = clasificar_mecanismo_identidad("cualquier texto", pais="uy")
    assert resultado == NO_CLASIFICABLE


# --- fail-safe: respuesta no reconocible / vacía ----------------------------------


def test_mecanismo_identidad_respuesta_no_reconocible_devuelve_no_clasificable(monkeypatch):
    _disponible(monkeypatch)
    monkeypatch.setattr(
        asistente_captura.litellm,
        "completion",
        lambda *a, **k: _mock_respuesta("esto no es ninguna categoría válida"),
    )
    resultado = clasificar_mecanismo_identidad("cualquier texto", pais="mx")
    assert resultado == NO_CLASIFICABLE


def test_mecanismo_identidad_respuesta_vacia_devuelve_no_clasificable(monkeypatch):
    _disponible(monkeypatch)
    monkeypatch.setattr(asistente_captura.litellm, "completion", lambda *a, **k: _mock_respuesta(""))
    resultado = clasificar_mecanismo_identidad("cualquier texto", pais="mx")
    assert resultado == NO_CLASIFICABLE


# --- espía: model/api_key/timeout correctos ---------------------------------------


def test_mecanismo_identidad_llm_recibe_model_api_key_y_timeout_correctos(monkeypatch):
    _disponible(monkeypatch)

    llamadas = []

    def _completion_espia(*args, **kwargs):
        llamadas.append(kwargs)
        return _mock_respuesta("propio")

    monkeypatch.setattr(asistente_captura.litellm, "completion", _completion_espia)

    clasificar_mecanismo_identidad("cualquier texto", pais="mx")

    assert len(llamadas) == 1
    assert llamadas[0]["model"] == "deepseek/deepseek-v4-pro"
    assert llamadas[0]["api_key"] == "sk-test"
    assert llamadas[0]["timeout"] == asistente_captura.TIMEOUT_SEGUNDOS
    assert llamadas[0]["extra_body"] == {"thinking": {"type": "disabled"}}

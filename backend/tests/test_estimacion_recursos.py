"""Tests de app/ia/estimacion_recursos.py -- mismo patrón que test_sugerencia_libre.py."""

from app.adaptadores.llm import estimacion_recursos
from app.adaptadores.llm.estimacion_recursos import ADVERTENCIA, generar_estimacion_recursos

_BRECHA = {"variable": "documentos_digitalizados", "paso_administrativo": "Digitalizar el expediente"}


def _mock_respuesta(texto: str) -> dict:
    return {"choices": [{"message": {"content": texto}}]}


def test_sin_brechas_devuelve_none_sin_llamar_ningun_llm(monkeypatch):
    def _no_debe_llamarse(*args, **kwargs):
        raise AssertionError("no debía intentarse ninguna llamada sin brechas")

    monkeypatch.setattr(estimacion_recursos, "obtener_rutas_generacion", lambda **_kw: ["local"])
    monkeypatch.setattr(estimacion_recursos, "esta_disponible", lambda ruta, **_kw: _no_debe_llamarse())

    assert generar_estimacion_recursos([], {}, "mx") is None


def test_sin_ninguna_ruta_disponible_devuelve_none(monkeypatch):
    monkeypatch.setattr(estimacion_recursos, "obtener_rutas_generacion", lambda **_kw: ["calidad"])
    monkeypatch.setattr(estimacion_recursos, "esta_disponible", lambda ruta, **_kw: False)

    assert generar_estimacion_recursos([_BRECHA], {}, "mx") is None


def test_con_brechas_y_ruta_disponible_devuelve_texto_y_advertencia(monkeypatch):
    monkeypatch.setattr(estimacion_recursos, "obtener_rutas_generacion", lambda **_kw: ["calidad"])
    monkeypatch.setattr(estimacion_recursos, "esta_disponible", lambda ruta, **_kw: True)
    monkeypatch.setattr(estimacion_recursos, "api_key_de", lambda ruta, **_kw: "sk-test")
    monkeypatch.setattr(
        estimacion_recursos.litellm, "completion", lambda **kwargs: _mock_respuesta("Estimación del mock.")
    )

    resultado = generar_estimacion_recursos([_BRECHA], {}, "mx")

    assert resultado == {"texto": "Estimación del mock.", "advertencia": ADVERTENCIA}


def test_todas_las_rutas_fallan_devuelve_none(monkeypatch):
    monkeypatch.setattr(estimacion_recursos, "obtener_rutas_generacion", lambda **_kw: ["calidad"])
    monkeypatch.setattr(estimacion_recursos, "esta_disponible", lambda ruta, **_kw: True)
    monkeypatch.setattr(estimacion_recursos, "api_key_de", lambda ruta, **_kw: "sk-test")

    def _completion_falla(**kwargs):
        raise RuntimeError("fallo simulado de red")

    monkeypatch.setattr(estimacion_recursos.litellm, "completion", _completion_falla)

    assert generar_estimacion_recursos([_BRECHA], {}, "mx") is None


def test_brechas_quedan_envueltas_en_delimitador_aleatorio(monkeypatch):
    prompt_capturado = {}

    def _completion_espia(**kwargs):
        prompt_capturado["texto"] = kwargs["messages"][0]["content"]
        return _mock_respuesta("ok")

    monkeypatch.setattr(estimacion_recursos, "obtener_rutas_generacion", lambda **_kw: ["calidad"])
    monkeypatch.setattr(estimacion_recursos, "esta_disponible", lambda ruta, **_kw: True)
    monkeypatch.setattr(estimacion_recursos, "api_key_de", lambda ruta, **_kw: "sk-test")
    monkeypatch.setattr(estimacion_recursos.litellm, "completion", _completion_espia)

    generar_estimacion_recursos([_BRECHA], {}, "mx")

    prompt = prompt_capturado["texto"]
    apertura_inicio = prompt.index("<brechas_del_plan_")
    marca = prompt[apertura_inicio : prompt.index(">", apertura_inicio) + 1]
    cierre_esperado = marca.replace("<brechas_del_plan_", "</brechas_del_plan_")
    assert cierre_esperado in prompt
    assert "Digitalizar el expediente" in prompt


def test_volumen_demanda_y_tramite_concurrente_se_incluyen_en_el_prompt(monkeypatch):
    prompt_capturado = {}

    def _completion_espia(**kwargs):
        prompt_capturado["texto"] = kwargs["messages"][0]["content"]
        return _mock_respuesta("ok")

    monkeypatch.setattr(estimacion_recursos, "obtener_rutas_generacion", lambda **_kw: ["calidad"])
    monkeypatch.setattr(estimacion_recursos, "esta_disponible", lambda ruta, **_kw: True)
    monkeypatch.setattr(estimacion_recursos, "api_key_de", lambda ruta, **_kw: "sk-test")
    monkeypatch.setattr(estimacion_recursos.litellm, "completion", _completion_espia)

    respuestas = {
        "volumen_demanda_anual": "mas_10000",
        "tramite_concurrente": True,
        "tramite_concurrente_detalle": "Catastro estatal",
    }
    generar_estimacion_recursos([_BRECHA], respuestas, "mx")

    prompt = prompt_capturado["texto"]
    assert "más de 10,000 solicitudes al año" in prompt
    assert "Catastro estatal" in prompt


def test_sin_volumen_ni_concurrencia_no_agrega_bloque_de_tramite(monkeypatch):
    prompt_capturado = {}

    def _completion_espia(**kwargs):
        prompt_capturado["texto"] = kwargs["messages"][0]["content"]
        return _mock_respuesta("ok")

    monkeypatch.setattr(estimacion_recursos, "obtener_rutas_generacion", lambda **_kw: ["calidad"])
    monkeypatch.setattr(estimacion_recursos, "esta_disponible", lambda ruta, **_kw: True)
    monkeypatch.setattr(estimacion_recursos, "api_key_de", lambda ruta, **_kw: "sk-test")
    monkeypatch.setattr(estimacion_recursos.litellm, "completion", _completion_espia)

    generar_estimacion_recursos([_BRECHA], {}, "mx")

    assert "Contexto de este trámite específico" not in prompt_capturado["texto"]

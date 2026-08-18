"""Tests del verificador (F9). Ninguna llamada real a un LLM --
`litellm.completion` siempre monkeypatcheado. Cubre las dos capas en su orden
estricto (compuerta determinista de `verificador_citas.py`, siempre; veredicto LLM
vía `economico`, solo si hay `DEEPSEEK_API_KEY`, nunca como requisito) y el
booleano fail-closed de la capa LLM. El caso negativo real (narrativa que inventa
una norma) vive en `test_verificador_citas.py`, sin necesitar ningún LLM -- ya no
en un test contra Ollama real: `local`/phi3 se retiró de la cadena de veredicto LLM
tras confirmar que no discrimina fidelidad de forma confiable (docs/plan-
implementacion-e1-bis-capa-ia-local.md sección 9)."""

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

NARRATIVA_CON_ARTICULO_INVENTADO = (
    "Este trámite debe completarse conforme al Artículo 999 de la Ley Federal de "
    "Trámites Digitales, dentro de un plazo máximo de 10 días naturales."
)


def _brecha_llm(narrativa: str) -> dict:
    return {**BRECHA_DETERMINISTA, "narrativa": narrativa}


def _mock_respuesta(texto: str) -> dict:
    return {"choices": [{"message": {"content": texto}}]}


# --- (a) sin ninguna API de pago: la compuerta determinista sola decide --------


def test_sin_economico_narrativa_fiel_aprueba_sin_llamar_llm(monkeypatch):
    """Antes, sin ninguna ruta de verificación disponible, esto rechazaba siempre
    -- el modo llm 100% local quedaba inalcanzable. Ahora la compuerta
    determinista (sin citas/números fabricados) basta por sí sola."""
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: False)

    def _completion_no_debe_llamarse(*args, **kwargs):
        raise AssertionError("litellm.completion no debía invocarse sin economico disponible")

    monkeypatch.setattr(verificador.litellm, "completion", _completion_no_debe_llamarse)

    contenido_llm = {"resumen_narrativo": "x", "brechas": [_brecha_llm("narrativa fiel, sin citas")]}
    assert verificar_contenido(contenido_llm, CONTENIDO_DETERMINISTA) is True


def test_sin_economico_narrativa_con_articulo_inventado_rechaza(monkeypatch):
    """La compuerta determinista rechaza aunque no haya ningún LLM disponible para
    contradecirla -- este es el caso real que motivó todo el rediseño (F9,
    docs/plan-implementacion-e1-bis-capa-ia-local.md sección 9)."""
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: False)
    monkeypatch.setattr(
        verificador.litellm,
        "completion",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debía llamarse")),
    )

    contenido_llm = {"resumen_narrativo": "x", "brechas": [_brecha_llm(NARRATIVA_CON_ARTICULO_INVENTADO)]}
    assert verificar_contenido(contenido_llm, CONTENIDO_DETERMINISTA) is False


# --- (a2) con economico disponible, la compuerta determinista corre PRIMERO ----


def test_con_economico_disponible_la_compuerta_determinista_rechaza_sin_llamar_llm(monkeypatch):
    """Orden estricto: si la compuerta determinista rechaza, ni siquiera se llama
    al LLM -- un "SI" de economico nunca puede rescatar una cita fabricada."""
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test")

    def _completion_no_debe_llamarse(*args, **kwargs):
        raise AssertionError("litellm.completion no debía invocarse -- la compuerta ya rechazó")

    monkeypatch.setattr(verificador.litellm, "completion", _completion_no_debe_llamarse)

    contenido_llm = {"resumen_narrativo": "x", "brechas": [_brecha_llm(NARRATIVA_CON_ARTICULO_INVENTADO)]}
    assert verificar_contenido(contenido_llm, CONTENIDO_DETERMINISTA) is False


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
        # Sin citas/números -- pasa la compuerta determinista; el rechazo viene
        # de la capa LLM, que es lo que este test mide.
        "brechas": [_brecha_llm("narrativa que contradice el sentido de los datos, sin citar nada nuevo")],
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


# --- (e3) puntuación/comillas/énfasis envolventes se toleran, pero NUNCA prefix-match ---


def test_veredicto_con_puntuacion_envolvente_aprueba(monkeypatch):
    """Un modelo de pocos parámetros (ej. phi3) puede envolver la respuesta en
    puntuación trivial ("SI.", "**SI**", '"SÍ"') incluso con temperature=0 -- eso
    debe tolerarse. Ninguno de estos casos es un prefix-match: se exige que TODO
    el resto (tras despojar la puntuación envolvente) sea exactamente "SI"/"SÍ"."""
    for respuesta_cruda in ('SI.', '"SÍ"', '**SI**', '  si.  ', "(SI)"):
        monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
        monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test")
        monkeypatch.setattr(
            verificador.litellm, "completion", lambda *a, **k: _mock_respuesta(respuesta_cruda)
        )
        contenido_llm = {"resumen_narrativo": "x", "brechas": [_brecha_llm("narrativa fiel")]}
        assert verificar_contenido(contenido_llm, CONTENIDO_DETERMINISTA) is True, respuesta_cruda


def test_veredicto_con_apertura_concesiva_no_es_prefix_match_rechaza(monkeypatch):
    """Regresión explícita contra relajar el parser a prefix-match: "sin embargo" y
    "si bien" son aperturas concesivas comunes en español -- un modelo divagando
    puede empezar así para señalar que la narrativa SÍ tiene un problema. Aprobar
    por empezar con "SI" convertiría el fail-closed en un falso-aprobado
    sistemático. También cubre una respuesta truncada por max_tokens=10 a media
    frase ("SI, LA NARRA...")."""
    for respuesta_cruda in (
        "SIN EMBARGO, LA NARRATIVA CONTRADICE EL SENTIDO DE LOS DATOS",
        "SI BIEN LA NARRATIVA ES CLARA, CONTRADICE LA FUENTE NORMATIVA",
        "SI, LA NARRA",
    ):
        monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
        monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test")
        monkeypatch.setattr(
            verificador.litellm, "completion", lambda *a, **k: _mock_respuesta(respuesta_cruda)
        )
        contenido_llm = {"resumen_narrativo": "x", "brechas": [_brecha_llm("narrativa fiel")]}
        assert verificar_contenido(contenido_llm, CONTENIDO_DETERMINISTA) is False, respuesta_cruda


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
    assert llamadas[0]["model"] == "deepseek/deepseek-v4-pro"
    assert llamadas[0]["api_key"] == "sk-test-economico"
    assert llamadas[0]["timeout"] == obtener_ruta("economico").timeout_segundos
    assert llamadas[0]["temperature"] == 0
    assert llamadas[0]["max_tokens"] == 10
    assert llamadas[0]["stop"] == ["\n"]
    assert llamadas[0]["extra_body"] == {"thinking": {"type": "disabled"}}


# --- (i) sin brechas en ambos lados -> True (nada que auditar, no hay discrepancia) ---


def test_sin_brechas_en_ambos_lados_devuelve_true_sin_llamar(monkeypatch):
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test")

    def _completion_no_debe_llamarse(*args, **kwargs):
        raise AssertionError("litellm.completion no debía invocarse sin brechas que auditar")

    monkeypatch.setattr(verificador.litellm, "completion", _completion_no_debe_llamarse)

    contenido_vacio = {"resumen_narrativo": "no hay brechas", "brechas": []}
    assert verificar_contenido(contenido_vacio, contenido_vacio) is True

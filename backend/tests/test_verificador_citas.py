"""Tests de la compuerta determinista de F9 (backend/app/ia/verificador_citas.py).
Sin LLM, sin mocks de red -- son funciones puras de texto."""

from app.ia.verificador_citas import citas_y_numeros_son_fieles

BRECHA_DETERMINISTA = {
    "paso_administrativo": "Suscribir convenio de homologación con la e.firma del SAT",
    "paso_tecnico": "Integrar verificación de firma con estándar abierto (PAdES/XAdES)",
    "paso_organizacional": "Capacitar a funcionarios de mostrador en uso del certificado",
    "por_que_importa": "Bloquea el paso de índice 2 a 3 (transaccional completo)",
    "fuente_normativa": "LNETB art. 25-III; ley estatal + convenio e.firma SAT",
}


def test_narrativa_sin_ninguna_cita_es_fiel_trivialmente():
    narrativa = "Se recomienda avanzar con la integración técnica correspondiente."
    assert citas_y_numeros_son_fieles(narrativa, BRECHA_DETERMINISTA) is True


def test_narrativa_que_repite_la_cita_real_es_fiel():
    narrativa = (
        "Conforme a LNETB art. 25-III, debe suscribirse convenio de homologación "
        "con la e.firma del SAT."
    )
    assert citas_y_numeros_son_fieles(narrativa, BRECHA_DETERMINISTA) is True


def test_narrativa_que_reformula_el_prefijo_del_articulo_sigue_siendo_fiel():
    """Mismo identificador numérico ("25-III"), prefijo reformulado ("artículo" en
    vez de "art.") -- no debe rechazarse solo por la forma de citar."""
    narrativa = "Según el artículo 25-III de la LNETB, corresponde suscribir el convenio."
    assert citas_y_numeros_son_fieles(narrativa, BRECHA_DETERMINISTA) is True


def test_narrativa_con_articulo_inventado_se_rechaza():
    narrativa = (
        "Este trámite debe completarse conforme al Artículo 999 de la Ley Federal "
        "de Trámites Digitales."
    )
    assert citas_y_numeros_son_fieles(narrativa, BRECHA_DETERMINISTA) is False


def test_narrativa_con_plazo_inventado_se_rechaza():
    narrativa = "El trámite debe completarse dentro de un plazo máximo de 10 días naturales."
    assert citas_y_numeros_son_fieles(narrativa, BRECHA_DETERMINISTA) is False


def test_narrativa_con_acronimo_inventado_se_rechaza():
    narrativa = "Debe cumplirse conforme a la STT y su reglamento correspondiente."
    assert citas_y_numeros_son_fieles(narrativa, BRECHA_DETERMINISTA) is False


def test_numero_sin_unidad_de_tiempo_no_activa_falso_rechazo():
    """"índice 2 a 3" ya está en los datos de referencia (por_que_importa) -- pero
    aunque no lo estuviera, un número suelto sin unidad de tiempo no es una
    afirmación normativa verificable y no debe activar el chequeo."""
    narrativa = "Esto permite avanzar del índice 2 al 3 en la escala de madurez."
    assert citas_y_numeros_son_fieles(narrativa, BRECHA_DETERMINISTA) is True


def test_identificador_corto_no_coincide_por_accidente_con_numero_largo_no_relacionado():
    """Regresión del chequeo por límites de palabra: la referencia contiene "1250"
    (no relacionado); citar un "artículo 25" inventado no debe aprobarse solo
    porque "25" aparece como substring de "1250"."""
    brecha = {**BRECHA_DETERMINISTA, "fuente_normativa": "Presupuesto de referencia: USD 1250"}
    narrativa = "Conforme al artículo 25 de la ley aplicable."
    assert citas_y_numeros_son_fieles(narrativa, brecha) is False


def test_decreto_inventado_se_rechaza():
    narrativa = "Conforme al Decreto 12345 se exige un trámite adicional."
    assert citas_y_numeros_son_fieles(narrativa, BRECHA_DETERMINISTA) is False


def test_campo_ausente_en_brecha_no_rompe_la_funcion():
    brecha_incompleta = {"paso_administrativo": "Hacer el trámite correspondiente."}
    narrativa = "Hacer el trámite correspondiente, sin ninguna cita normativa."
    assert citas_y_numeros_son_fieles(narrativa, brecha_incompleta) is True

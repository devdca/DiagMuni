import pytest

from app.dominio.madurez import calcular_indice_madurez
from app.dominio.plantillas import generar_contenido_degradado
from app.dominio.tipos_tramite_loader import (
    cargar_tipos_tramite,
    completar_respuestas_no_aplicables,
    evaluar_brechas_adicionales,
)

_RESPUESTAS_SIN_MOTOR_PAGOS = {
    "documentos_digitalizados": True,
    "firma_electronica_habilitada": True,
    "interoperabilidad": True,
    "mecanismo_identidad": "propio",
}


def test_generico_no_excluye_nada():
    tipos = cargar_tipos_tramite()
    assert "generico" in tipos
    assert tipos["generico"].variables_excluidas == frozenset()


def test_catalogo_incluye_los_3_tipos_de_cuajimalpa():
    tipos = cargar_tipos_tramite()
    assert {"licencia_funcionamiento", "licencia_uso_suelo", "registro_civil"} <= set(tipos.keys())


def test_completar_respuestas_no_aplicables_solo_completa_lo_excluido():
    respuestas = {"documentos_digitalizados": True}
    resultado = completar_respuestas_no_aplicables("registro_civil", respuestas)

    assert resultado["motor_pagos"] is True  # excluido -> satisfecho, nunca brecha
    assert resultado["documentos_digitalizados"] is True  # lo real, sin tocar


def test_completar_respuestas_no_aplicables_respeta_lo_ya_contestado():
    # si el funcionario sí contestó una variable que además está excluida para
    # este tipo (ej. cambió de tipo a medio cuestionario), su respuesta real gana.
    respuestas = {"motor_pagos": False}
    resultado = completar_respuestas_no_aplicables("registro_civil", respuestas)

    assert resultado["motor_pagos"] is False


def test_completar_respuestas_no_aplicables_generico_no_cambia_nada():
    respuestas = {"motor_pagos": False, "firma_electronica_habilitada": False}
    resultado = completar_respuestas_no_aplicables("generico", respuestas)

    assert resultado == respuestas


def test_tipo_inexistente_lanza_key_error():
    with pytest.raises(KeyError):
        completar_respuestas_no_aplicables("no-existe", {})


def test_variable_excluida_no_tapa_el_indice_de_madurez():
    # sin completar: motor_pagos ausente cae al valor_por_defecto (false) de
    # indice_madurez.yaml y tapa el índice en nivel 2 -- un trámite que
    # legítimamente no cobra en línea (registro_civil) no debería quedar
    # atascado ahí solo por no preguntarle algo que no le aplica.
    assert calcular_indice_madurez(_RESPUESTAS_SIN_MOTOR_PAGOS) == 2

    completadas = completar_respuestas_no_aplicables("registro_civil", _RESPUESTAS_SIN_MOTOR_PAGOS)
    assert calcular_indice_madurez(completadas) == 4


def test_variable_excluida_no_aparece_como_brecha_falsa():
    completadas = completar_respuestas_no_aplicables("registro_civil", _RESPUESTAS_SIN_MOTOR_PAGOS)
    contenido = generar_contenido_degradado(completadas, "mx")

    variables = {b["variable"] for b in contenido["brechas"]}
    assert "motor_pagos" not in variables


def test_generico_no_tiene_variables_adicionales():
    assert cargar_tipos_tramite()["generico"].variables_adicionales == ()


def test_cada_tipo_de_cuajimalpa_tiene_su_variable_adicional_propia():
    tipos = cargar_tipos_tramite()
    assert {va.variable for va in tipos["licencia_funcionamiento"].variables_adicionales} == {
        "inspeccion_digital_habilitada"
    }
    assert {va.variable for va in tipos["licencia_uso_suelo"].variables_adicionales} == {
        "consulta_zonificacion_en_linea"
    }
    assert {va.variable for va in tipos["registro_civil"].variables_adicionales} == {
        "verificacion_duplicados_automatica"
    }


def test_evaluar_brechas_adicionales_false_es_brecha():
    brechas = evaluar_brechas_adicionales("registro_civil", {"verificacion_duplicados_automatica": False})
    assert len(brechas) == 1
    assert brechas[0]["variable"] == "verificacion_duplicados_automatica"
    assert brechas[0]["componente_recomendado"] is None  # sin OSS recomendado todavía, no inventado


def test_evaluar_brechas_adicionales_true_no_es_brecha():
    assert evaluar_brechas_adicionales("registro_civil", {"verificacion_duplicados_automatica": True}) == []


def test_evaluar_brechas_adicionales_sin_contestar_no_es_brecha():
    # ausente != false -- no se fuerza una brecha por una pregunta sin contestar
    # todavía (a media captura), mismo criterio que el resto del motor.
    assert evaluar_brechas_adicionales("registro_civil", {}) == []


def test_evaluar_brechas_adicionales_generico_siempre_vacio():
    assert evaluar_brechas_adicionales("generico", {"cualquier_cosa": False}) == []

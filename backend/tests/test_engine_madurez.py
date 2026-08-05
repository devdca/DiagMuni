"""Tests basados en tabla (docs/TRD.md, "Testing"): mismos datos de entrada -> mismo
índice, independiente del país (la lógica de nivel no depende de mx/uy, solo del
catálogo de acciones — ver docs/engine/madurez.py)."""

import pytest

from app.engine.madurez import calcular_indice_global, calcular_indice_madurez

CASOS = [
    # (respuestas, indice_esperado, motivo)
    ({}, 0, "sin nada capturado, documentos_digitalizados ausente = false por default"),
    ({"documentos_digitalizados": False}, 0, "explícitamente sin digitalizar"),
    ({"documentos_digitalizados": True}, 1, "digitalizado pero sin pagos ni firma = informativo"),
    (
        {"documentos_digitalizados": True, "motor_pagos": True},
        2,
        "una sola de pagos/firma = transaccional parcial",
    ),
    (
        {"documentos_digitalizados": True, "firma_electronica_habilitada": True},
        2,
        "una sola de pagos/firma (firma) = transaccional parcial",
    ),
    (
        {"documentos_digitalizados": True, "motor_pagos": True, "firma_electronica_habilitada": True},
        3,
        "ambas pagos y firma, sin interoperabilidad/identidad = transaccional completo",
    ),
    (
        {
            "documentos_digitalizados": True,
            "motor_pagos": True,
            "firma_electronica_habilitada": True,
            "interoperabilidad": True,
            "mecanismo_identidad": "llave_mx",
        },
        4,
        "todo cumplido = proactivo e interoperable",
    ),
    (
        {
            "documentos_digitalizados": True,
            "motor_pagos": True,
            "firma_electronica_habilitada": True,
            "interoperabilidad": True,
            "mecanismo_identidad": "ninguno",
        },
        3,
        "interoperabilidad sin identidad no alcanza 4",
    ),
]


@pytest.mark.parametrize("respuestas,indice_esperado,motivo", CASOS)
def test_calcular_indice_madurez(respuestas, indice_esperado, motivo):
    assert calcular_indice_madurez(respuestas) == indice_esperado, motivo


def test_reproducibilidad_mismos_datos_mismo_indice():
    respuestas = {"documentos_digitalizados": True, "motor_pagos": True}
    assert calcular_indice_madurez(respuestas) == calcular_indice_madurez(dict(respuestas))


# (indices, promedio_esperado, motivo) -- panel resumen (docs/PRD.md línea 32,
# docs/app-flow.md línea 54): promedio solo de los ya diagnosticados, `None`
# nunca cuenta como 0 ni penaliza.
CASOS_INDICE_GLOBAL = [
    ([], None, "sin trámites catalogados"),
    ([None, None], None, "trámites catalogados pero ninguno diagnosticado todavía"),
    ([2], 2.0, "un solo trámite diagnosticado"),
    ([2, None, 4], 3.0, "los no diagnosticados no cuentan ni penalizan"),
    ([0, 1, 2, 3, 4], 2.0, "promedio simple de todos los niveles"),
    ([1, 2], 1.5, "promedio no entero, no se redondea en el motor"),
]


@pytest.mark.parametrize("indices,promedio_esperado,motivo", CASOS_INDICE_GLOBAL)
def test_calcular_indice_global(indices, promedio_esperado, motivo):
    assert calcular_indice_global(indices) == promedio_esperado, motivo

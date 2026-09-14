from app.dominio.resumen_plan import (
    calcular_orden_sugerido,
    calcular_progreso_historico,
    calcular_resumen_inversion,
    calcular_resumen_personal,
)

_COMPONENTE_A = {
    "nombre_componente": "Mayan EDMS",
    "costo_licenciamiento": {"moneda_local": "0", "usd": "0"},
    "costo_infraestructura": {"moneda_local": "114.55/mes (piso verificado)", "usd": "6.60/mes"},
    "costo_implementacion": {"moneda_local": "[NO VERIFICADO]", "usd": "[NO VERIFICADO]"},
}

_COMPONENTE_B = {
    "nombre_componente": "DSS",
    "costo_licenciamiento": {"moneda_local": "0", "usd": "0"},
    "costo_infraestructura": {"moneda_local": "[NO VERIFICADO]", "usd": "[NO VERIFICADO]"},
    "costo_implementacion": {"moneda_local": "500.00", "usd": "28.80"},
}


def _brecha(variable: str, componente: dict | None = None, prerrequisitos: list[str] | None = None) -> dict:
    return {
        "variable": variable,
        "paso_organizacional": f"organizar {variable}",
        "prerrequisitos": prerrequisitos or [],
        "componente_recomendado": componente,
    }


def test_resumen_inversion_suma_solo_montos_parseables():
    brechas = [
        _brecha("documentos_digitalizados", _COMPONENTE_A),
        _brecha("firma_electronica_habilitada", _COMPONENTE_B),
    ]

    resumen = calcular_resumen_inversion(brechas, "mx")

    assert resumen["moneda_local_codigo"] == "MXN"
    assert resumen["inversion_unica_estimada"] == {"moneda_local": "500.00", "usd": "28.80"}
    assert resumen["costo_recurrente_mensual_estimado"] == {"moneda_local": "114.55", "usd": "6.60"}
    assert resumen["brechas_totales"] == 2
    assert resumen["brechas_con_componente_software"] == 2
    assert len(resumen["componentes"]) == 2


def test_resumen_inversion_dedupe_por_nombre_componente():
    brechas = [_brecha("a", _COMPONENTE_A), _brecha("b", _COMPONENTE_A)]

    resumen = calcular_resumen_inversion(brechas, "mx")

    assert len(resumen["componentes"]) == 1
    assert resumen["costo_recurrente_mensual_estimado"]["moneda_local"] == "114.55"


def test_resumen_inversion_sin_componentes_devuelve_montos_null():
    resumen = calcular_resumen_inversion([_brecha("gobernanza_institucional")], "uy")

    assert resumen["moneda_local_codigo"] == "UYU"
    assert resumen["inversion_unica_estimada"] == {"moneda_local": None, "usd": None}
    assert resumen["costo_recurrente_mensual_estimado"] == {"moneda_local": None, "usd": None}
    assert resumen["brechas_con_componente_software"] == 0


def test_resumen_personal_deduplica_paso_organizacional_y_lee_perfil():
    brechas = [_brecha("a"), _brecha("a"), _brecha("b")]
    respuestas = {"personal_area_ti": 3, "personal_total_gobierno": 40, "capacitacion_personal_tic_anual": True}

    resumen = calcular_resumen_personal(brechas, respuestas, "mx")

    assert resumen["acciones_organizacionales"] == ["organizar a", "organizar b"]
    assert resumen["personal_ti_actual"] == 3
    assert resumen["personal_total_gobierno"] == 40
    assert resumen["capacitacion_anual_vigente"] is True


def test_resumen_personal_sin_perfil_devuelve_none():
    resumen = calcular_resumen_personal([_brecha("a")], {}, "mx")

    assert resumen["personal_ti_actual"] is None
    assert resumen["personal_total_gobierno"] is None
    assert resumen["capacitacion_anual_vigente"] is None


def test_resumen_personal_incluye_costo_referencia_verificado_mx():
    resumen = calcular_resumen_personal([_brecha("a")], {}, "mx")

    assert resumen["costo_referencia_personal_ti"]["salario_mensual_promedio"] == "21318"
    assert resumen["costo_referencia_personal_ti"]["moneda"] == "MXN"


def test_resumen_personal_costo_referencia_no_verificado_uy():
    resumen = calcular_resumen_personal([_brecha("a")], {}, "uy")

    assert resumen["costo_referencia_personal_ti"]["salario_mensual_promedio"] == "[NO VERIFICADO]"


def test_orden_sugerido_agrupa_por_prerrequisitos():
    brechas = [
        _brecha("a"),
        _brecha("b", prerrequisitos=["Documentos digitalizados"]),
        _brecha("c"),
    ]

    orden = calcular_orden_sugerido(brechas)

    assert orden == {"sin_prerrequisitos": ["a", "c"], "con_prerrequisitos": ["b"]}


def test_progreso_historico_calcula_resueltas_nuevas_persistentes():
    anteriores = [{"variable": "motor_pagos"}, {"variable": "interoperabilidad"}]
    actuales = [{"variable": "interoperabilidad"}, {"variable": "version_accesible"}]

    progreso = calcular_progreso_historico(actuales, anteriores)

    assert progreso == {
        "brechas_resueltas": ["motor_pagos"],
        "brechas_nuevas": ["version_accesible"],
        "brechas_persistentes": ["interoperabilidad"],
    }


def test_progreso_historico_sin_version_anterior_no_hay_resueltas_ni_persistentes():
    progreso = calcular_progreso_historico([{"variable": "motor_pagos"}], [])

    assert progreso == {"brechas_resueltas": [], "brechas_nuevas": ["motor_pagos"], "brechas_persistentes": []}

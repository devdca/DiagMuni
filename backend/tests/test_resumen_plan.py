from app.dominio.resumen_plan import (
    calcular_factibilidad,
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


# --- Fase A: calcular_factibilidad ------------------------------------------------------


def test_factibilidad_requiere_nueva_norma_gana_sobre_cualquier_costo():
    brecha = {"requiere_nueva_norma": True, "componente_recomendado": _COMPONENTE_B}
    respuestas = {"presupuesto_tic_anual": 1_000_000, "poblacion_total": 5_000}

    assert calcular_factibilidad(brecha, respuestas) == "nueva_norma"


def test_factibilidad_config_existente_sin_componente_recomendado():
    brecha = _brecha("a", componente=None)
    respuestas = {"presupuesto_tic_anual": 100_000, "poblacion_total": 50_000}

    assert calcular_factibilidad(brecha, respuestas) == "config_existente"


def test_factibilidad_config_existente_sin_presupuesto_tic_anual_capturado():
    brecha = _brecha("a", componente=_COMPONENTE_B)

    assert calcular_factibilidad(brecha, {}) == "config_existente"


def test_factibilidad_config_existente_bajo_el_umbral():
    # _COMPONENTE_B: implementacion 500.00 + licenciamiento 0 = 500.00 de costo.
    # Presupuesto 100,000 * umbral 0.10 (bracket 20k-100k) = 10,000 -- 500 no lo supera.
    brecha = _brecha("a", componente=_COMPONENTE_B)
    respuestas = {"presupuesto_tic_anual": 100_000, "poblacion_total": 50_000}

    assert calcular_factibilidad(brecha, respuestas) == "config_existente"


def test_factibilidad_presupuesto_extraordinario_sobre_el_umbral():
    # Mismo costo (500.00), presupuesto mucho menor: 1,000 * 0.10 = 100 -- 500 sí lo supera.
    brecha = _brecha("a", componente=_COMPONENTE_B)
    respuestas = {"presupuesto_tic_anual": 1_000, "poblacion_total": 50_000}

    assert calcular_factibilidad(brecha, respuestas) == "presupuesto_extraordinario"


def test_factibilidad_sin_poblacion_usa_el_bracket_mas_tolerante():
    # Sin poblacion_total: bracket más tolerante (0.15). Presupuesto 1,000 * 0.15 =
    # 150 -- el costo de 500.00 igual lo supera, pero con un presupuesto mayor
    # (4,000 * 0.15 = 600) ya no lo supera, a diferencia de si cayera en el
    # bracket más estricto (0.05, que sí lo marcaría extraordinario: 4,000*0.05=200).
    brecha = _brecha("a", componente=_COMPONENTE_B)
    respuestas = {"presupuesto_tic_anual": 4_000}

    assert calcular_factibilidad(brecha, respuestas) == "config_existente"

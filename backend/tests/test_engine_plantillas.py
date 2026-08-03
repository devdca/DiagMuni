from app.engine.plantillas import generar_contenido_degradado

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


def test_sin_nada_detecta_todas_las_brechas_mx():
    contenido = generar_contenido_degradado(RESPUESTAS_SIN_NADA, "mx")
    variables_detectadas = {b["variable"] for b in contenido["brechas"]}
    assert variables_detectadas == {
        "documentos_digitalizados",
        "motor_pagos",
        "firma_electronica_habilitada",
        "interoperabilidad",
        "proteccion_datos_incompleta",
        "mecanismo_identidad",
    }


def test_nivel_maximo_sin_brechas_no_fuerza_recomendacion():
    # docs/app-flow.md, "Casos especiales": trámite sin brechas no fuerza una recomendación.
    contenido = generar_contenido_degradado(RESPUESTAS_NIVEL_MAXIMO, "mx")
    assert contenido["brechas"] == []
    assert "no hay" in contenido["resumen_narrativo"].lower()


def test_firma_electronica_cita_norma_correcta_por_pais():
    contenido_mx = generar_contenido_degradado(RESPUESTAS_SIN_NADA, "mx")
    contenido_uy = generar_contenido_degradado(RESPUESTAS_SIN_NADA, "uy")
    firma_mx = next(b for b in contenido_mx["brechas"] if b["variable"] == "firma_electronica_habilitada")
    firma_uy = next(b for b in contenido_uy["brechas"] if b["variable"] == "firma_electronica_habilitada")
    assert "LNETB" in firma_mx["fuente_normativa"]
    assert "18.600" in firma_uy["fuente_normativa"]
    assert firma_mx["fuente_normativa"] != firma_uy["fuente_normativa"]


def test_brecha_incluye_componente_recomendado_con_datos_del_catalogo():
    contenido = generar_contenido_degradado(RESPUESTAS_SIN_NADA, "mx")
    firma = next(b for b in contenido["brechas"] if b["variable"] == "firma_electronica_habilitada")
    assert firma["componente_recomendado"]["nombre_componente"] == "DSS (Digital Signature Service) — esig/dss"
    assert firma["componente_recomendado"]["licencia"] == "LGPL-2.1"


def test_componente_recomendado_selecciona_moneda_segun_pais():
    contenido_mx = generar_contenido_degradado(RESPUESTAS_SIN_NADA, "mx")
    contenido_uy = generar_contenido_degradado(RESPUESTAS_SIN_NADA, "uy")
    doc_mx = next(b for b in contenido_mx["brechas"] if b["variable"] == "documentos_digitalizados")
    doc_uy = next(b for b in contenido_uy["brechas"] if b["variable"] == "documentos_digitalizados")

    assert doc_mx["componente_recomendado"]["moneda_local_codigo"] == "MXN"
    assert doc_uy["componente_recomendado"]["moneda_local_codigo"] == "UYU"

    infra_mx = doc_mx["componente_recomendado"]["costo_infraestructura"]
    infra_uy = doc_uy["componente_recomendado"]["costo_infraestructura"]
    assert infra_mx["moneda_local"] == (
        "114.55/mes (piso mínimo verificado; ver nota_infraestructura para el escalón recomendado, no verificado)"
    )
    assert infra_uy["moneda_local"] == (
        "264.65/mes (piso mínimo verificado; ver nota_infraestructura para el escalón recomendado, no verificado)"
    )
    assert infra_mx["usd"] == infra_uy["usd"]


def test_costo_no_verificado_se_preserva_literal():
    contenido = generar_contenido_degradado(RESPUESTAS_SIN_NADA, "mx")
    for brecha in contenido["brechas"]:
        assert brecha["componente_recomendado"]["costo_implementacion"]["moneda_local"] == "[NO VERIFICADO]"


def test_nota_advertencia_presente_solo_cuando_el_catalogo_la_declara():
    contenido_uy = generar_contenido_degradado(RESPUESTAS_SIN_NADA, "uy")
    interoperabilidad = next(b for b in contenido_uy["brechas"] if b["variable"] == "interoperabilidad")
    assert interoperabilidad["componente_recomendado"]["nota_advertencia"] is not None
    assert "PDI" in interoperabilidad["componente_recomendado"]["nota_advertencia"]

    mecanismo_identidad = next(b for b in contenido_uy["brechas"] if b["variable"] == "mecanismo_identidad")
    assert mecanismo_identidad["componente_recomendado"]["nota_advertencia"] is None


def test_wiring_no_altera_deteccion_de_brechas():
    contenido_sin_nada = generar_contenido_degradado(RESPUESTAS_SIN_NADA, "mx")
    variables_detectadas = {b["variable"] for b in contenido_sin_nada["brechas"]}
    assert variables_detectadas == {
        "documentos_digitalizados",
        "motor_pagos",
        "firma_electronica_habilitada",
        "interoperabilidad",
        "proteccion_datos_incompleta",
        "mecanismo_identidad",
    }
    assert len(contenido_sin_nada["brechas"]) == 6

    contenido_nivel_maximo = generar_contenido_degradado(RESPUESTAS_NIVEL_MAXIMO, "mx")
    assert contenido_nivel_maximo["brechas"] == []

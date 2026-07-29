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

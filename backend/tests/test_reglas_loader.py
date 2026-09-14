from app.dominio.reglas_loader import cargar_catalogo, criterio_se_cumple

# 6 variables del cuestionario por trámite + 8 variables de contexto/capacidad
# institucional con criterio_deteccion real (transversales, a nivel de todo el
# gobierno, no del trámite) + 14 variables adicionales del cuestionario de
# trámite (también transversales, no gatillan un nivel del índice de madurez).
VARIABLES_ESPERADAS = {
    "documentos_digitalizados",
    "motor_pagos",
    "firma_electronica_habilitada",
    "interoperabilidad",
    "proteccion_datos_incompleta",
    "mecanismo_identidad",
    "autoridad_gobernanza_digital",
    "agenda_simplificacion_publicada",
    "portal_datos_abiertos_existe",
    "linea_atencion_ciudadana_centralizada",
    "capacitacion_personal_tic_anual",
    "protocolo_ciberseguridad_existe",
    "enlace_notificado_formalmente",
    "convenio_colaboracion_estado",
    "tramite_completo_en_linea",
    "registrado_portal_ciudadano_unico",
    "notificaciones_automaticas",
    "plazo_respuesta_publicado",
    "silencio_administrativo_definido",
    "disponible_movil",
    "mecanismo_quejas_digital",
    "fundamento_juridico_vigente",
    "costo_publicado_en_linea",
    "personal_capacitado_tramite_digital",
    "version_accesible",
    "atencion_lengua_indigena",
    "medicion_tiempo_satisfaccion",
    "revisado_ultimos_12_meses",
    "requisitos_publicados_claramente",
}


def test_catalogo_carga_las_29_variables():
    catalogo = cargar_catalogo()
    assert set(catalogo.keys()) == VARIABLES_ESPERADAS


def test_cada_regla_tiene_mx_y_uy():
    catalogo = cargar_catalogo()
    for variable, regla in catalogo.items():
        assert "mx" in regla.acciones, f"{variable} sin acción para mx"
        assert "uy" in regla.acciones, f"{variable} sin acción para uy"


def test_criterio_booleano():
    assert criterio_se_cumple("firma_electronica_habilitada == false", {"firma_electronica_habilitada": False})
    assert not criterio_se_cumple("firma_electronica_habilitada == false", {"firma_electronica_habilitada": True})


def test_criterio_string():
    assert criterio_se_cumple('mecanismo_identidad == "ninguno"', {"mecanismo_identidad": "ninguno"})
    assert not criterio_se_cumple('mecanismo_identidad == "ninguno"', {"mecanismo_identidad": "llave_mx"})


def test_criterio_ausente_no_se_cumple_sin_lanzar():
    # `criterio_se_cumple` usa dict.get (nunca KeyError) -- una clave ausente del
    # dict de respuestas simplemente no cumple el criterio, no revienta el motor.
    assert not criterio_se_cumple("autoridad_gobernanza_digital == false", {})


def test_autoridad_gobernanza_digital_es_transversal_categoria_gobernanza_institucional():
    regla = cargar_catalogo()["autoridad_gobernanza_digital"]
    assert regla.criterio_deteccion == "autoridad_gobernanza_digital == false"
    for pais in ("mx", "uy"):
        assert regla.acciones[pais].categoria_catalogo == "gobernanza_institucional"


def test_las_5_variables_institucionales_nuevas_tienen_criterio_false_y_ambos_paises():
    catalogo = cargar_catalogo()
    variables = (
        "agenda_simplificacion_publicada",
        "portal_datos_abiertos_existe",
        "linea_atencion_ciudadana_centralizada",
        "capacitacion_personal_tic_anual",
        "protocolo_ciberseguridad_existe",
    )
    for variable in variables:
        regla = catalogo[variable]
        assert regla.criterio_deteccion == f"{variable} == false"
        assert "mx" in regla.acciones
        assert "uy" in regla.acciones


def test_requisitos_publicados_claramente_tiene_criterio_false_y_ambos_paises():
    regla = cargar_catalogo()["requisitos_publicados_claramente"]
    assert regla.criterio_deteccion == "requisitos_publicados_claramente == false"
    assert "mx" in regla.acciones
    assert "uy" in regla.acciones


def test_las_2_variables_de_gobernanza_nuevas_tienen_criterio_false_y_ambos_paises():
    catalogo = cargar_catalogo()
    variables = ("enlace_notificado_formalmente", "convenio_colaboracion_estado")
    for variable in variables:
        regla = catalogo[variable]
        assert regla.criterio_deteccion == f"{variable} == false"
        assert "mx" in regla.acciones
        assert "uy" in regla.acciones
        assert regla.acciones["mx"].categoria_catalogo == "gobernanza_institucional"


def test_las_14_variables_de_tramite_nuevas_tienen_criterio_false_y_ambos_paises():
    catalogo = cargar_catalogo()
    variables = (
        "tramite_completo_en_linea",
        "registrado_portal_ciudadano_unico",
        "notificaciones_automaticas",
        "plazo_respuesta_publicado",
        "silencio_administrativo_definido",
        "disponible_movil",
        "mecanismo_quejas_digital",
        "fundamento_juridico_vigente",
        "costo_publicado_en_linea",
        "personal_capacitado_tramite_digital",
        "version_accesible",
        "atencion_lengua_indigena",
        "medicion_tiempo_satisfaccion",
        "revisado_ultimos_12_meses",
    )
    for variable in variables:
        regla = catalogo[variable]
        assert regla.criterio_deteccion == f"{variable} == false"
        assert "mx" in regla.acciones
        assert "uy" in regla.acciones

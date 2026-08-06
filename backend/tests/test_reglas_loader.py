from app.engine.reglas_loader import cargar_catalogo, criterio_se_cumple

# 6 variables del cuestionario por trámite + `autoridad_gobernanza_digital`
# (única de las 7 variables de contexto/capacidad institucional con
# criterio_deteccion real -- entregables/fase-2/variables-contexto-institucional.md,
# sección 3.1).
VARIABLES_ESPERADAS = {
    "documentos_digitalizados",
    "motor_pagos",
    "firma_electronica_habilitada",
    "interoperabilidad",
    "proteccion_datos_incompleta",
    "mecanismo_identidad",
    "autoridad_gobernanza_digital",
}


def test_catalogo_carga_las_7_variables():
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

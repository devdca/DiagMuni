from app.engine.reglas_loader import cargar_catalogo, criterio_se_cumple

VARIABLES_ESPERADAS = {
    "documentos_digitalizados",
    "motor_pagos",
    "firma_electronica_habilitada",
    "interoperabilidad",
    "proteccion_datos_incompleta",
    "mecanismo_identidad",
}


def test_catalogo_carga_las_6_variables():
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

from app.dominio.costos_personal_loader import costo_personal_referencia_para


def test_mx_tiene_salario_verificado():
    datos = costo_personal_referencia_para("mx")

    assert datos is not None
    assert datos["salario_mensual_promedio"] == "21318"
    assert datos["moneda"] == "MXN"
    assert "economia.gob.mx" in datos["fuente"]


def test_uy_no_tiene_salario_verificado():
    datos = costo_personal_referencia_para("uy")

    assert datos is not None
    assert datos["salario_mensual_promedio"] == "[NO VERIFICADO]"


def test_pais_desconocido_devuelve_none():
    assert costo_personal_referencia_para("ar") is None

from app.engine.catalogo_loader import cargar_catalogo_oss, componente_recomendado_para

CATEGORIAS_ESPERADAS = {
    "modulo_cifrado_datos",
    "gestor_expediente_electronico",
    "modulo_firma_electronica",
    "identidad_federada",
    "conector_interoperabilidad",
    "adaptador_pasarela_pago",
}


def test_catalogo_carga_las_6_categorias():
    catalogo = cargar_catalogo_oss()
    assert set(catalogo.keys()) == CATEGORIAS_ESPERADAS


def test_componente_recomendado_para_resuelve_las_6_categorias_en_mx_y_uy():
    for categoria in CATEGORIAS_ESPERADAS:
        for pais in ("mx", "uy"):
            resultado = componente_recomendado_para(categoria, pais)
            assert resultado is not None
            assert resultado["nombre_componente"]


def test_categoria_inexistente_devuelve_none():
    assert componente_recomendado_para("categoria_que_no_existe", "mx") is None


def test_pais_fuera_de_mx_uy_devuelve_none():
    assert componente_recomendado_para("modulo_cifrado_datos", "ar") is None

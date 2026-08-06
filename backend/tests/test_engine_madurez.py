"""Tests basados en tabla (docs/TRD.md, "Testing"): mismos datos de entrada -> mismo
índice, independiente del país (la lógica de nivel no depende de mx/uy, solo del
catálogo de acciones — ver docs/engine/madurez.py)."""

from pathlib import Path

import pytest
import yaml

from app.engine import madurez
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


@pytest.fixture(autouse=True)
def _limpiar_cache_reglas_indice():
    """Cada test de esta sección monkeypatchea INDICE_MADUREZ_YAML; sin limpiar el
    lru_cache antes y después, un test contaminaría el config cargado por el resto
    de la suite (incluyendo tests de otros módulos que también llaman a
    calcular_indice_madurez)."""
    madurez._cargar_reglas_indice_madurez.cache_clear()
    yield
    madurez._cargar_reglas_indice_madurez.cache_clear()


def test_config_alterna_cambia_el_indice_sin_tocar_python(tmp_path):
    """Prueba que calcular_indice_madurez es config-driven de verdad: con un YAML
    de reglas distinto al real (mismos campos de entrada, umbrales distintos),
    el mismo diccionario de respuestas produce un índice distinto -- sin cambiar
    una sola línea de código Python."""
    respuestas = {
        "documentos_digitalizados": True,
        "motor_pagos": True,
        "firma_electronica_habilitada": True,
    }
    # Con la config real, esta combinación es nivel 3 (ver CASOS arriba).
    assert calcular_indice_madurez(respuestas) == 3

    config_alterna = tmp_path / "indice_madurez_alterno.yaml"
    config_alterna.write_text(
        """
        version: "test"
        reglas:
          - nivel: 9
            condiciones:
              - campo: documentos_digitalizados
                operador: "=="
                valor: true
                valor_por_defecto: false
          - nivel: 0
            condiciones:
              - campo: documentos_digitalizados
                operador: "=="
                valor: false
                valor_por_defecto: false
        """,
        encoding="utf-8",
    )
    original_path = madurez.INDICE_MADUREZ_YAML
    madurez.INDICE_MADUREZ_YAML = config_alterna
    madurez._cargar_reglas_indice_madurez.cache_clear()
    try:
        assert calcular_indice_madurez(respuestas) == 9
    finally:
        madurez.INDICE_MADUREZ_YAML = original_path


def test_config_vacia_falla_de_forma_controlada_en_vez_de_usar_logica_fija(tmp_path):
    """Si el YAML no cubre ninguna regla, calcular_indice_madurez debe fallar
    ruidosamente (ValueError) en vez de "recordar" la lógica 0-4 original -- eso
    confirma que el archivo se usa de verdad y no hay un fallback Python oculto."""
    config_vacia = tmp_path / "indice_madurez_vacio.yaml"
    config_vacia.write_text('version: "test"\nreglas: []\n', encoding="utf-8")

    original_path = madurez.INDICE_MADUREZ_YAML
    madurez.INDICE_MADUREZ_YAML = config_vacia
    madurez._cargar_reglas_indice_madurez.cache_clear()
    try:
        with pytest.raises(ValueError, match="indice_madurez.yaml"):
            calcular_indice_madurez({"documentos_digitalizados": True})
    finally:
        madurez.INDICE_MADUREZ_YAML = original_path


def test_config_real_se_carga_desde_archivo(tmp_path):
    """Confirma que el archivo real indice_madurez.yaml (no una copia embebida en
    el test) es el que efectivamente se lee: se apunta el loader directamente al
    archivo de producción vía su ruta absoluta y se valida que produce el mismo
    índice que devuelve calcular_indice_madurez sobre casos ya cubiertos en CASOS."""
    ruta_real = Path(__file__).resolve().parents[1] / "app" / "engine" / "indice_madurez.yaml"
    assert ruta_real == madurez.INDICE_MADUREZ_YAML.resolve()
    assert ruta_real.exists()

    contenido = yaml.safe_load(ruta_real.read_text(encoding="utf-8"))
    assert contenido["reglas"], "indice_madurez.yaml no debe declarar un catálogo de reglas vacío"

    madurez._cargar_reglas_indice_madurez.cache_clear()
    respuestas = {"documentos_digitalizados": True}
    assert calcular_indice_madurez(respuestas) == 1

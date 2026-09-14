"""Carga app/engine/catalogo/costos_personal.yaml -- mismo patrón que
reglas_loader.py: el catálogo nunca se transcribe a código Python.
"""

from functools import lru_cache
from pathlib import Path

import yaml

COSTOS_PERSONAL_YAML = Path(__file__).parent / "catalogo" / "costos_personal.yaml"


@lru_cache(maxsize=1)
def _cargar() -> dict:
    with COSTOS_PERSONAL_YAML.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def costo_personal_referencia_para(pais: str) -> dict | None:
    """`None` si el país no está en el catálogo. Un `salario_mensual_promedio` de
    "[NO VERIFICADO]" es un valor real del catálogo (no un error) -- quien
    consume esto decide cómo mostrarlo, igual que "[NO VERIFICADO]" en
    costos_oss.yaml."""
    datos = _cargar().get(pais)
    if datos is None:
        return None
    return dict(datos)

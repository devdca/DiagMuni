"""Carga el catálogo OSS de componentes recomendados y costos paramétricos
(F4/F5, docs/PRD.md líneas 53-54) desde YAML.

Mismo patrón que reglas_loader.py: el catálogo nunca se transcribe a código
Python, este módulo solo lee los archivos en tiempo de ejecución.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

CATALOGO_DIR = Path(__file__).parent / "catalogo"
COMPONENTES_YAML = CATALOGO_DIR / "componentes_oss.yaml"
COSTOS_YAML = CATALOGO_DIR / "costos_oss.yaml"

_MONEDA_POR_PAIS: dict[str, tuple[str, str]] = {
    "mx": ("MXN", "mxn"),
    "uy": ("UYU", "uyu"),
}


@dataclass(frozen=True)
class ComponenteCatalogo:
    nombre_componente: str
    licencia: str
    url_repositorio: str
    nota: str | None
    fuente_licencia: str
    fuente_actividad: str
    costo_licenciamiento_mxn: str
    costo_licenciamiento_uyu: str
    costo_licenciamiento_usd: str
    costo_infraestructura_mxn: str
    costo_infraestructura_uyu: str
    costo_infraestructura_usd: str
    costo_implementacion_mxn: str
    costo_implementacion_uyu: str
    costo_implementacion_usd: str
    fuente_costo: str
    fecha_consulta: str


@lru_cache(maxsize=1)
def cargar_catalogo_oss() -> dict[str, ComponenteCatalogo]:
    """Un dict por categoria_catalogo — ej. catalogo['gestor_expediente_electronico'].

    Combina componentes_oss.yaml (F4) y costos_oss.yaml (F5); ambos deben declarar
    exactamente el mismo conjunto de claves bajo `componentes:` — si no coinciden,
    falla ruidosamente en el primer acceso en vez de degradar en silencio.
    """
    with COMPONENTES_YAML.open(encoding="utf-8") as f:
        datos_componentes = yaml.safe_load(f)["componentes"]
    with COSTOS_YAML.open(encoding="utf-8") as f:
        datos_costos = yaml.safe_load(f)["componentes"]

    claves_componentes = set(datos_componentes.keys())
    claves_costos = set(datos_costos.keys())
    if claves_componentes != claves_costos:
        raise ValueError(
            "componentes_oss.yaml y costos_oss.yaml no tienen las mismas claves: "
            f"solo en componentes={claves_componentes - claves_costos}, "
            f"solo en costos={claves_costos - claves_componentes}"
        )

    catalogo: dict[str, ComponenteCatalogo] = {}
    for categoria, componente in datos_componentes.items():
        costo = datos_costos[categoria]
        catalogo[categoria] = ComponenteCatalogo(
            nombre_componente=componente["nombre_componente"],
            licencia=componente["licencia"],
            url_repositorio=componente["url_repositorio"],
            nota=componente.get("nota"),
            fuente_licencia=componente["fuente_licencia"],
            fuente_actividad=componente["fuente_actividad"],
            costo_licenciamiento_mxn=costo["costo_licenciamiento_mxn"],
            costo_licenciamiento_uyu=costo["costo_licenciamiento_uyu"],
            costo_licenciamiento_usd=costo["costo_licenciamiento_usd"],
            costo_infraestructura_mxn=costo["costo_infraestructura_mxn"],
            costo_infraestructura_uyu=costo["costo_infraestructura_uyu"],
            costo_infraestructura_usd=costo["costo_infraestructura_usd"],
            costo_implementacion_mxn=costo["costo_implementacion_mxn"],
            costo_implementacion_uyu=costo["costo_implementacion_uyu"],
            costo_implementacion_usd=costo["costo_implementacion_usd"],
            fuente_costo=costo["fuente_costo"],
            fecha_consulta=costo["fecha_consulta"],
        )
    return catalogo


def componente_recomendado_para(categoria_catalogo: str, pais: str) -> dict | None:
    """Arma el objeto `componente_recomendado` (forma exacta en
    entregables/fase-2/catalogo-oss-wiring.md sección 1.1) para una brecha ya
    decidida por engine/reglas/*.yaml. Devuelve `None` si la categoría o el país
    no resuelven en el catálogo — nunca lanza una excepción que tumbe el plan."""
    catalogo = cargar_catalogo_oss()
    componente = catalogo.get(categoria_catalogo)
    if componente is None:
        return None

    moneda_pais = _MONEDA_POR_PAIS.get(pais)
    if moneda_pais is None:
        return None
    moneda_local_codigo, sufijo = moneda_pais

    return {
        "nombre_componente": componente.nombre_componente,
        "licencia": componente.licencia,
        "url_repositorio": componente.url_repositorio,
        "moneda_local_codigo": moneda_local_codigo,
        "costo_licenciamiento": {
            "moneda_local": getattr(componente, f"costo_licenciamiento_{sufijo}"),
            "usd": componente.costo_licenciamiento_usd,
        },
        "costo_infraestructura": {
            "moneda_local": getattr(componente, f"costo_infraestructura_{sufijo}"),
            "usd": componente.costo_infraestructura_usd,
        },
        "costo_implementacion": {
            "moneda_local": getattr(componente, f"costo_implementacion_{sufijo}"),
            "usd": componente.costo_implementacion_usd,
        },
        "nota_advertencia": componente.nota,
        "fuente_licencia": componente.fuente_licencia,
        "fuente_actividad": componente.fuente_actividad,
        "fuente_costo": componente.fuente_costo,
        "fecha_verificacion": componente.fecha_consulta,
    }

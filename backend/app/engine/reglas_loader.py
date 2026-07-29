"""Carga el catálogo de reglas brecha->acción desde YAML (docs/TRD.md).

Regla dura de docs/plan-implementacion.md, fase C: el catálogo nunca se transcribe a
código Python, ni siquiera "temporalmente" — este módulo solo lee los archivos en
tiempo de ejecución.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

REGLAS_DIR = Path(__file__).parent / "reglas"


@dataclass(frozen=True)
class AccionPais:
    paso_administrativo: str
    paso_tecnico: str
    paso_organizacional: str
    prerrequisitos: list[str]
    por_que_importa: str
    fuente_normativa: str
    categoria_catalogo: str


@dataclass(frozen=True)
class Regla:
    version: str
    variable: str
    criterio_deteccion: str
    acciones: dict[str, AccionPais]  # clave: "mx" | "uy"


def _parse_criterio(criterio: str) -> tuple[str, object]:
    """Parsea "clave == valor" sin eval() — el criterio viene de YAML versionado
    por el equipo, pero evitar eval() mantiene el motor determinista y auditable
    sin depender de que el YAML sea siempre confiable."""
    clave, _, valor_str = criterio.partition("==")
    clave = clave.strip()
    valor_str = valor_str.strip()
    if valor_str == "true":
        valor: object = True
    elif valor_str == "false":
        valor = False
    elif valor_str.startswith('"') and valor_str.endswith('"'):
        valor = valor_str[1:-1]
    else:
        valor = valor_str
    return clave, valor


def criterio_se_cumple(criterio: str, respuestas: dict) -> bool:
    clave, valor_esperado = _parse_criterio(criterio)
    return respuestas.get(clave) == valor_esperado


@lru_cache(maxsize=1)
def cargar_catalogo() -> dict[str, Regla]:
    """Un dict por variable — ej. catalogo['firma_electronica_habilitada']."""
    catalogo: dict[str, Regla] = {}
    for archivo in sorted(REGLAS_DIR.glob("*.yaml")):
        with archivo.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        acciones = {pais: AccionPais(**contenido) for pais, contenido in data["acciones"].items()}
        regla = Regla(
            version=str(data["version"]),
            variable=data["variable"],
            criterio_deteccion=data["criterio_deteccion"],
            acciones=acciones,
        )
        catalogo[regla.variable] = regla
    return catalogo

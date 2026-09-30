"""Carga el catálogo de reglas brecha->acción desde YAML. Regla dura: el
catálogo nunca se transcribe a código Python, ni siquiera "temporalmente"."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

REGLAS_DIR = Path(__file__).parent / "reglas"

# "municipal" son los YAML directo en REGLAS_DIR; "estatal"/"federal" viven en
# subcarpetas propias -- nunca un eje anidado dentro de `acciones`, porque
# `cargar_catalogo` instancia `AccionPais(**contenido)` directo por kwargs.
NIVELES_GOBIERNO_VALIDOS = ("municipal", "estatal", "federal")


@dataclass(frozen=True)
class AccionPais:
    paso_administrativo: str
    paso_tecnico: str
    paso_organizacional: str
    prerrequisitos: list[str]
    por_que_importa: str
    fuente_normativa: str
    categoria_catalogo: str
    # Si la acción exige una reforma/norma nueva antes de ejecutarse (ver
    # `resumen_plan.calcular_factibilidad`). Default False por retrocompatibilidad.
    requiere_nueva_norma: bool = False


@dataclass(frozen=True)
class Regla:
    version: str
    variable: str
    criterio_deteccion: str
    acciones: dict[str, AccionPais]  # clave: "mx" | "uy"


def _parse_criterio(criterio: str) -> tuple[str, object]:
    """Parsea "clave == valor" sin eval() -- mantiene el motor determinista y
    auditable sin depender de que el YAML sea siempre confiable."""
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


def _cargar_directorio(directorio: Path) -> dict[str, Regla]:
    catalogo: dict[str, Regla] = {}
    if not directorio.is_dir():
        return catalogo
    for archivo in sorted(directorio.glob("*.yaml")):
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


@lru_cache(maxsize=32)
def cargar_catalogo(nivel_gobierno: str = "municipal", tipo_tramite: str | None = None) -> dict[str, Regla]:
    """Un dict por variable. `nivel_gobierno` selecciona la carpeta de origen
    (ver NIVELES_GOBIERNO_VALIDOS).

    `tipo_tramite` (override opcional): si `REGLAS_DIR/<nivel>/<tipo_tramite>/`
    existe, sus YAML se cargan ENCIMA del catálogo genérico -- una regla con la
    misma `variable` ahí reemplaza por completo a la genérica. Existe porque
    dos trámites del mismo nivel pueden tener fundamento normativo distinto
    para la misma variable (ej. SAT vs. transparencia a nivel federal).

    `maxsize=32`: varias combinaciones (nivel, tipo_tramite) conviven en caché."""
    if nivel_gobierno not in NIVELES_GOBIERNO_VALIDOS:
        raise ValueError(f"Nivel de gobierno '{nivel_gobierno}' no soportado -- use {NIVELES_GOBIERNO_VALIDOS}.")
    directorio_base = REGLAS_DIR if nivel_gobierno == "municipal" else REGLAS_DIR / nivel_gobierno

    catalogo = _cargar_directorio(directorio_base)
    if tipo_tramite is not None:
        catalogo.update(_cargar_directorio(directorio_base / tipo_tramite))
    return catalogo

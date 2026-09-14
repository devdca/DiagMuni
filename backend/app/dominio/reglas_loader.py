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

# Fase A de la expansión a los tres órdenes de gobierno: "municipal" son los 29
# YAML históricos en REGLAS_DIR directo (cero migración de contenido existente);
# "estatal"/"federal" viven en subcarpetas nuevas (REGLAS_DIR/estatal,
# REGLAS_DIR/federal) -- carpetas separadas, no un tercer eje anidado dentro de
# `acciones`, porque `cargar_catalogo` instancia `AccionPais(**contenido)`
# directo por kwargs y un nivel de anidación extra rompería ese parseo.
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
    # Fase A: si la acción exige una reforma/norma nueva antes de poder
    # ejecutarse (ej. crear una autoridad que hoy no existe en ese gobierno),
    # en vez de ser solo cuestión de presupuesto/config -- ver
    # `resumen_plan.calcular_factibilidad`. Default False para no romper los
    # 29 YAML municipales existentes, que no declaran este campo.
    requiere_nueva_norma: bool = False


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
    """Un dict por variable — ej. catalogo['firma_electronica_habilitada'].

    `nivel_gobierno` ("municipal" default, o "estatal"/"federal") selecciona la
    carpeta de origen -- ver NIVELES_GOBIERNO_VALIDOS.

    `tipo_tramite` (Fase A, override opcional): si `REGLAS_DIR/<nivel>/<tipo_tramite>/`
    existe, sus YAML se cargan ENCIMA del catálogo genérico del nivel -- una
    regla con la misma `variable` en la carpeta específica del trámite
    reemplaza por completo a la genérica (no se fusionan campos), y una
    variable que solo exista en la carpeta específica se agrega. Existe porque
    dos trámites reales del mismo nivel_gobierno pueden tener fundamento
    normativo distinto para la misma variable (ej. SAT vs. transparencia a
    nivel federal: plazos de respuesta y requisitos de identidad muy
    distintos) -- una sola versión "genérica federal" mentiría sobre uno de
    los dos. Si un trámite no necesita override, simplemente no tiene carpeta
    y usa el catálogo genérico del nivel tal cual.

    `maxsize=32` (no 1): varias combinaciones (nivel, tipo_tramite) deben
    convivir en caché, no invalidarse entre sí."""
    if nivel_gobierno not in NIVELES_GOBIERNO_VALIDOS:
        raise ValueError(f"Nivel de gobierno '{nivel_gobierno}' no soportado -- use {NIVELES_GOBIERNO_VALIDOS}.")
    directorio_base = REGLAS_DIR if nivel_gobierno == "municipal" else REGLAS_DIR / nivel_gobierno

    catalogo = _cargar_directorio(directorio_base)
    if tipo_tramite is not None:
        catalogo.update(_cargar_directorio(directorio_base / tipo_tramite))
    return catalogo

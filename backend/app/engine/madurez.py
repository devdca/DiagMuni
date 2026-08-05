"""Cálculo del índice de madurez (F2), puro y determinista — docs/PRD.md define los
5 niveles: 0 presencial en papel, 1 informativo, 2 transaccional parcial,
3 transaccional completo, 4 proactivo e interoperable.

El nivel se deriva de `indice_madurez.yaml`, nunca de lógica Python fija: este
módulo solo carga y evalúa esa config en tiempo de ejecución, mismo principio que
`reglas_loader.py`/`catalogo_loader.py` para los catálogos de F3/F4.

Regla de versionado (docs/TRD.md): cambiar una regla normativa que afecta el
resultado entrada→salida (ej. qué combinación de variables produce cada nivel)
exige subir VERSION_MOTOR; un diagnóstico ya persistido nunca se recalcula con
una versión distinta a la que lo produjo (docs/backend-schema.md, campo
version_motor). Un cambio que preserva ese comportamiento (ej. mover la lógica
de Python a config, sin alterar qué nivel resulta de cada combinación) no
constituye una regla normativa nueva y no requiere subir VERSION_MOTOR.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

VERSION_MOTOR = "1.0"

INDICE_MADUREZ_YAML = Path(__file__).parent / "indice_madurez.yaml"


@dataclass(frozen=True)
class CondicionIndice:
    campo: str
    operador: str
    valor: bool | str
    valor_por_defecto: bool | str


@dataclass(frozen=True)
class ReglaIndice:
    nivel: int
    condiciones: tuple[CondicionIndice, ...]


def _condicion_se_cumple(condicion: CondicionIndice, respuestas: dict) -> bool:
    """Evalúa "campo operador valor" sin eval() — misma filosofía que
    criterio_se_cumple en reglas_loader.py, extendida con un valor por defecto
    propio de cada campo (los booleanos ausentes cuentan como false; los campos de
    texto como mecanismo_identidad ausentes cuentan como su propio valor neutro)."""
    valor_obtenido = respuestas.get(condicion.campo, condicion.valor_por_defecto)
    if isinstance(condicion.valor, bool):
        valor_obtenido = bool(valor_obtenido)
    if condicion.operador == "==":
        return valor_obtenido == condicion.valor
    if condicion.operador == "!=":
        return valor_obtenido != condicion.valor
    raise ValueError(f"operador de condición no soportado en indice_madurez.yaml: {condicion.operador!r}")


def _nivel_aplica(regla: ReglaIndice, respuestas: dict) -> bool:
    """Todas las condiciones de la regla deben cumplirse (Y lógico) para que el
    nivel aplique — las combinaciones que requerirían "O" se enumeran como reglas
    separadas en el YAML en vez de introducir un operador "O" acá."""
    return all(_condicion_se_cumple(condicion, respuestas) for condicion in regla.condiciones)


@lru_cache(maxsize=1)
def _cargar_reglas_indice_madurez() -> tuple[ReglaIndice, ...]:
    """Reglas ordenadas tal como aparecen en el YAML: de la más específica (nivel
    más alto) a la más genérica (nivel más bajo) — gana la primera que aplica.

    El campo `version` de indice_madurez.yaml es metadato informativo (mismo
    patrón que `version` en engine/reglas/*.yaml vía reglas_loader.py): no se
    valida programáticamente contra VERSION_MOTOR -- quien sube una regla
    normativa real sube VERSION_MOTOR a mano, no este campo."""
    with INDICE_MADUREZ_YAML.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    reglas = []
    for regla_data in data["reglas"]:
        condiciones = tuple(CondicionIndice(**condicion) for condicion in regla_data["condiciones"])
        reglas.append(ReglaIndice(nivel=regla_data["nivel"], condiciones=condiciones))
    return tuple(reglas)


def calcular_indice_madurez(respuestas: dict) -> int:
    """Deriva el índice evaluando `indice_madurez.yaml` en orden hasta encontrar la
    primera regla cuyas condiciones se cumplen todas (ver "por qué importa" en cada
    YAML de engine/reglas/, que liga cada variable a un nivel):

    - documentos_digitalizados en false bloquea todo (nivel 0) — es prerrequisito
      de cualquier transaccionalidad (documentos_papel_digital.yaml).
    - motor_pagos y firma_electronica_habilitada bloquean, cada una, el paso a
      nivel 3 (transaccional completo) — con solo una de las dos, queda en
      "transaccional parcial" (nivel 2), no en 0/1.
    - interoperabilidad y mecanismo_identidad (distinto de "ninguno") son requisito
      de nivel 4 (proactivo e interoperable), solo alcanzable habiendo llegado a 3.

    proteccion_datos_incompleta NO participa aquí: es transversal (datos_personales.yaml),
    no gatilla un nivel específico del índice.
    """
    for regla in _cargar_reglas_indice_madurez():
        if _nivel_aplica(regla, respuestas):
            return regla.nivel
    raise ValueError("indice_madurez.yaml no tiene una regla que cubra estas respuestas")


def calcular_indice_global(indices: list[int | None]) -> float | None:
    """Índice global del panel resumen (docs/PRD.md línea 32, docs/app-flow.md
    línea 54 -- ninguno de los dos fija la fórmula, decidida acá): promedio de
    los trámites que ya tienen diagnóstico completo (`indice_madurez` no nulo).
    Los trámites sin diagnosticar (`None`) no cuentan en el promedio ni lo
    penalizan -- nunca se les asume un 0.

    Devuelve `None` si la lista está vacía o si nadie ha sido diagnosticado
    todavía (ningún trámite catalogado tiene aún un índice que promediar) --
    nunca lanza una excepción por ese caso."""
    diagnosticados = [indice for indice in indices if indice is not None]
    if not diagnosticados:
        return None
    return sum(diagnosticados) / len(diagnosticados)

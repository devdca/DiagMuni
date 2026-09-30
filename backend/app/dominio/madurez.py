"""Cálculo del índice de madurez (F2), puro y determinista — 5 niveles: 0
presencial en papel, 1 informativo, 2 transaccional parcial, 3 transaccional
completo, 4 proactivo e interoperable.

El nivel se deriva de `indice_madurez.yaml`, nunca de lógica Python fija.

Regla de versionado: cambiar una regla normativa que afecta el resultado
entrada→salida exige subir VERSION_MOTOR; un diagnóstico ya persistido nunca
se recalcula con una versión distinta a la que lo produjo."""

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
    """Evalúa "campo operador valor" sin eval(), con un valor por defecto propio
    de cada campo (los booleanos ausentes cuentan como false)."""
    valor_obtenido = respuestas.get(condicion.campo, condicion.valor_por_defecto)
    if isinstance(condicion.valor, bool):
        valor_obtenido = bool(valor_obtenido)
    if condicion.operador == "==":
        return valor_obtenido == condicion.valor
    if condicion.operador == "!=":
        return valor_obtenido != condicion.valor
    raise ValueError(f"operador de condición no soportado en indice_madurez.yaml: {condicion.operador!r}")


def _nivel_aplica(regla: ReglaIndice, respuestas: dict) -> bool:
    """Todas las condiciones deben cumplirse (Y lógico) -- las combinaciones "O"
    se enumeran como reglas separadas en el YAML."""
    return all(_condicion_se_cumple(condicion, respuestas) for condicion in regla.condiciones)


@lru_cache(maxsize=1)
def _cargar_reglas_indice_madurez() -> tuple[ReglaIndice, ...]:
    """Reglas ordenadas tal como aparecen en el YAML: de la más específica a la
    más genérica -- gana la primera que aplica. `version` del YAML es solo
    informativo, no se valida contra VERSION_MOTOR."""
    with INDICE_MADUREZ_YAML.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    reglas = []
    for regla_data in data["reglas"]:
        condiciones = tuple(CondicionIndice(**condicion) for condicion in regla_data["condiciones"])
        reglas.append(ReglaIndice(nivel=regla_data["nivel"], condiciones=condiciones))
    return tuple(reglas)


def calcular_indice_madurez(respuestas: dict) -> int:
    """Deriva el índice evaluando `indice_madurez.yaml` en orden:

    - `documentos_digitalizados` en false bloquea todo (nivel 0).
    - `motor_pagos`/`firma_electronica_habilitada` bloquean, cada una, el paso
      a nivel 3 -- con solo una, queda en nivel 2.
    - `interoperabilidad` y `mecanismo_identidad` (≠ "ninguno") son requisito
      de nivel 4.

    `proteccion_datos_incompleta` no participa aquí: es transversal, no gatilla
    un nivel específico."""
    for regla in _cargar_reglas_indice_madurez():
        if _nivel_aplica(regla, respuestas):
            return regla.nivel
    raise ValueError("indice_madurez.yaml no tiene una regla que cubra estas respuestas")


def calcular_indice_global(indices: list[int | None]) -> float | None:
    """Promedio de los trámites ya diagnosticados (`indice_madurez` no nulo).
    Los sin diagnosticar (`None`) no cuentan ni se penalizan -- nunca se les
    asume un 0. `None` si nadie ha sido diagnosticado todavía."""
    diagnosticados = [indice for indice in indices if indice is not None]
    if not diagnosticados:
        return None
    return sum(diagnosticados) / len(diagnosticados)

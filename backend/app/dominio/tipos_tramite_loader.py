"""Carga el catálogo de tipos de trámite desde YAML -- nunca se transcribe a
código Python. Decide qué variables del cuestionario se preguntan por tipo:
`documentos_digitalizados`, `proteccion_datos_incompleta` y
`mecanismo_identidad` son obligatorias siempre; solo `motor_pagos`,
`firma_electronica_habilitada` e `interoperabilidad` son excluibles.

`variables_adicionales`: preguntas propias de un tipo, nunca gatillan un nivel
del índice -- solo aparecen como brecha si la respuesta es `false`."""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from app.dominio.catalogo_loader import componente_recomendado_para

TIPOS_TRAMITE_PATH = Path(__file__).parent / "tipos_tramite.yaml"

VARIABLES_EXCLUIBLES = frozenset({"motor_pagos", "firma_electronica_habilitada", "interoperabilidad"})

# "satisfecho" = no bloquea un nivel de madurez ni aparece como brecha en el plan.
VALORES_SATISFECHOS: dict[str, object] = {
    "motor_pagos": True,
    "firma_electronica_habilitada": True,
    "interoperabilidad": True,
}


@dataclass(frozen=True)
class VariableAdicional:
    variable: str
    pregunta: str
    ayuda: str
    paso_administrativo: str
    paso_tecnico: str
    paso_organizacional: str
    prerrequisitos: list[str]
    por_que_importa: str
    fuente_normativa: str
    categoria_catalogo: str


@dataclass(frozen=True)
class TipoTramite:
    nombre: str
    etiqueta: str
    variables_excluidas: frozenset[str]
    variables_adicionales: tuple[VariableAdicional, ...] = field(default_factory=tuple)


@lru_cache(maxsize=1)
def cargar_tipos_tramite() -> dict[str, TipoTramite]:
    with TIPOS_TRAMITE_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    tipos: dict[str, TipoTramite] = {}
    for nombre, contenido in data["tipos"].items():
        variables_excluidas = frozenset(contenido.get("variables_excluidas", []))
        no_excluibles = variables_excluidas - VARIABLES_EXCLUIBLES
        if no_excluibles:
            raise ValueError(
                f"Tipo de trámite '{nombre}' excluye variable(s) no excluible(s): "
                f"{sorted(no_excluibles)}. Solo se puede excluir de {sorted(VARIABLES_EXCLUIBLES)}."
            )
        variables_adicionales = tuple(
            VariableAdicional(
                variable=va["variable"],
                pregunta=va["pregunta"],
                ayuda=va["ayuda"],
                paso_administrativo=va["paso_administrativo"],
                paso_tecnico=va["paso_tecnico"],
                paso_organizacional=va["paso_organizacional"],
                prerrequisitos=va.get("prerrequisitos", []),
                por_que_importa=va["por_que_importa"],
                fuente_normativa=va["fuente_normativa"],
                categoria_catalogo=va["categoria_catalogo"],
            )
            for va in contenido.get("variables_adicionales", [])
        )
        tipos[nombre] = TipoTramite(
            nombre=nombre,
            etiqueta=contenido["etiqueta"],
            variables_excluidas=variables_excluidas,
            variables_adicionales=variables_adicionales,
        )
    return tipos


def completar_respuestas_no_aplicables(tipo: str, respuestas: dict) -> dict:
    """`respuestas` real siempre gana. Lanza `KeyError` si `tipo` no está en
    el catálogo -- error de configuración real, no se degrada en silencio."""
    tipo_tramite = cargar_tipos_tramite()[tipo]
    satisfechas = {variable: VALORES_SATISFECHOS[variable] for variable in tipo_tramite.variables_excluidas}
    return {**satisfechas, **respuestas}


def _narrativa_adicional(va: VariableAdicional) -> str:
    return (
        f"{va.paso_administrativo}. {va.paso_tecnico}. {va.paso_organizacional}. "
        f"{va.por_que_importa} (fuente: {va.fuente_normativa})."
    )


def evaluar_brechas_adicionales(tipo: str, respuestas: dict, pais: str = "mx") -> list[dict]:
    """Brechas de las variables propias del tipo de trámite, mismo formato de
    dict que `generar_contenido_degradado`. `respuestas.get(variable) is
    False` es la brecha (pregunta en afirmativo: False = falta)."""
    tipo_tramite = cargar_tipos_tramite()[tipo]
    brechas = []
    for va in tipo_tramite.variables_adicionales:
        if respuestas.get(va.variable) is not False:
            continue
        brechas.append(
            {
                "variable": va.variable,
                "categoria_catalogo": va.categoria_catalogo,
                "paso_administrativo": va.paso_administrativo,
                "paso_tecnico": va.paso_tecnico,
                "paso_organizacional": va.paso_organizacional,
                "prerrequisitos": va.prerrequisitos,
                "por_que_importa": va.por_que_importa,
                "fuente_normativa": va.fuente_normativa,
                "narrativa": _narrativa_adicional(va),
                "componente_recomendado": componente_recomendado_para(va.categoria_catalogo, pais),
            }
        )
    return brechas

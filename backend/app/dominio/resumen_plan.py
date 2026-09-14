"""Síntesis determinista sobre el `contenido` ya generado de un plan -- sin ningún
LLM, mismo principio que el resto de `engine/` (motor determinista primero).

Todo lo de acá opera sobre datos que ya existen en cada brecha (`componente_recomendado`,
`paso_organizacional`, `prerrequisitos`) o en el perfil de gobierno ya capturado
(`respuestas`, fusionado por `_namespace_efectivo` en app/jobs/plan_job.py) -- nunca
inventa una cifra nueva. Donde un dato no está verificado, el resultado es `None`,
nunca un valor fabricado.
"""

import re
from decimal import Decimal

from app.dominio.costos_personal_loader import costo_personal_referencia_para

_PATRON_MONTO = re.compile(r"^\s*([\d,]+(?:\.\d+)?)")

_CODIGO_MONEDA_POR_PAIS = {"mx": "MXN", "uy": "UYU"}

_NOTA_COBERTURA_INVERSION = (
    "El presupuesto estimado solo suma montos verificados de componentes de software "
    "recomendados (los marcados \"[NO VERIFICADO]\" en el catálogo se excluyen del total, "
    "ver cada componente). Las brechas sin componente de software son acciones normativas "
    "u organizacionales sin costo de licenciamiento asociado."
)


def _parsear_monto(cadena: str) -> Decimal | None:
    """Extrae el monto inicial de un string de costo del catálogo OSS (ej. "114.55/mes
    (piso mínimo verificado...)" -> 114.55). Cadenas sin un número al inicio (ej.
    "[NO VERIFICADO]") devuelven `None` -- nunca se asume 0 donde no hay dato."""
    coincidencia = _PATRON_MONTO.match(cadena)
    if not coincidencia:
        return None
    return Decimal(coincidencia.group(1).replace(",", ""))


def _sumar_columna(componentes: list[dict], campo: str, clave_moneda: str) -> Decimal | None:
    total = Decimal("0")
    hubo_alguno = False
    for componente in componentes:
        monto = _parsear_monto(componente[campo][clave_moneda])
        if monto is not None:
            total += monto
            hubo_alguno = True
    return total.quantize(Decimal("0.01")) if hubo_alguno else None


def _sumar_opcionales(a: Decimal | None, b: Decimal | None) -> Decimal | None:
    if a is None and b is None:
        return None
    return (a or Decimal("0")) + (b or Decimal("0"))


def _formatear(monto: Decimal | None) -> str | None:
    return str(monto) if monto is not None else None


def calcular_resumen_inversion(brechas: list[dict], pais: str) -> dict:
    """Agrega `componente_recomendado` de todas las brechas -- deduplicado por
    `nombre_componente` (dos brechas con la misma `categoria_catalogo` resuelven al
    mismo componente, ver app/engine/catalogo_loader.py::componente_recomendado_para,
    función pura de categoria+país). Licenciamiento + implementación se suman como
    inversión única; infraestructura como costo recurrente mensual (todas las
    entradas de infraestructura en el catálogo hoy son mensuales o "no aplica")."""
    componentes_unicos: dict[str, dict] = {}
    for brecha in brechas:
        componente = brecha.get("componente_recomendado")
        if componente is None:
            continue
        componentes_unicos.setdefault(componente["nombre_componente"], componente)

    componentes = list(componentes_unicos.values())

    licenciamiento_local = _sumar_columna(componentes, "costo_licenciamiento", "moneda_local")
    implementacion_local = _sumar_columna(componentes, "costo_implementacion", "moneda_local")
    infraestructura_local = _sumar_columna(componentes, "costo_infraestructura", "moneda_local")
    licenciamiento_usd = _sumar_columna(componentes, "costo_licenciamiento", "usd")
    implementacion_usd = _sumar_columna(componentes, "costo_implementacion", "usd")
    infraestructura_usd = _sumar_columna(componentes, "costo_infraestructura", "usd")

    return {
        "moneda_local_codigo": _CODIGO_MONEDA_POR_PAIS.get(pais, ""),
        "inversion_unica_estimada": {
            "moneda_local": _formatear(_sumar_opcionales(licenciamiento_local, implementacion_local)),
            "usd": _formatear(_sumar_opcionales(licenciamiento_usd, implementacion_usd)),
        },
        "costo_recurrente_mensual_estimado": {
            "moneda_local": _formatear(infraestructura_local),
            "usd": _formatear(infraestructura_usd),
        },
        "componentes": componentes,
        "brechas_totales": len(brechas),
        "brechas_con_componente_software": sum(1 for b in brechas if b.get("componente_recomendado") is not None),
        "nota_cobertura": _NOTA_COBERTURA_INVERSION,
    }


def calcular_resumen_personal(brechas: list[dict], respuestas: dict, pais: str) -> dict:
    """`acciones_organizacionales` consolida `paso_organizacional` (dato que ya
    existe por brecha) una sola vez arriba, deduplicado, en el mismo orden en que
    aparecen las brechas. `costo_referencia_personal_ti` es el salario mensual
    verificado de app/engine/catalogo/costos_personal.yaml -- una cifra de
    referencia real (cuánto cuesta 1 puesto), nunca cuántas personas hacen falta
    (eso no es verificable con una fuente pública, ver app/ia/estimacion_recursos.py).
    El resto son campos del perfil de gobierno ya capturado (`respuestas`,
    fusionado vía `_namespace_efectivo`) -- `None` si el gobierno todavía no los
    llenó, nunca una cifra inventada de personal."""
    acciones_organizacionales: list[str] = []
    vistas: set[str] = set()
    for brecha in brechas:
        texto = brecha.get("paso_organizacional")
        if texto and texto not in vistas:
            vistas.add(texto)
            acciones_organizacionales.append(texto)

    return {
        "acciones_organizacionales": acciones_organizacionales,
        "personal_ti_actual": respuestas.get("personal_area_ti"),
        "personal_total_gobierno": respuestas.get("personal_total_gobierno"),
        "capacitacion_anual_vigente": respuestas.get("capacitacion_personal_tic_anual"),
        "costo_referencia_personal_ti": costo_personal_referencia_para(pais),
    }


def calcular_orden_sugerido(brechas: list[dict]) -> dict:
    """Agrupa por si `prerrequisitos` (ya existente por brecha) está vacío o no --
    no es un grafo de dependencias real (prerrequisitos es texto libre, no
    referencias resolubles a otra variable), es la lectura honesta de lo que el
    catálogo ya declara: qué se puede iniciar ya y qué depende de algo más."""
    return {
        "sin_prerrequisitos": [b["variable"] for b in brechas if not b.get("prerrequisitos")],
        "con_prerrequisitos": [b["variable"] for b in brechas if b.get("prerrequisitos")],
    }


def calcular_progreso_historico(brechas_actuales: list[dict], brechas_anteriores: list[dict]) -> dict:
    """Diff determinista por `variable` entre dos versiones de plan del mismo
    trámite -- se computa en lectura (app/api/planes.py), no se persiste, porque
    depende de dos filas de `plan_modernizacion` a la vez."""
    variables_actuales = {b["variable"] for b in brechas_actuales}
    variables_anteriores = {b["variable"] for b in brechas_anteriores}
    return {
        "brechas_resueltas": sorted(variables_anteriores - variables_actuales),
        "brechas_nuevas": sorted(variables_actuales - variables_anteriores),
        "brechas_persistentes": sorted(variables_actuales & variables_anteriores),
    }

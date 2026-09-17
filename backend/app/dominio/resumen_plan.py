"""Síntesis determinista sobre el `contenido` ya generado de un plan -- sin
ningún LLM. Opera solo sobre datos que ya existen (cada brecha, o el perfil de
gobierno ya capturado) -- nunca inventa una cifra. Sin dato verificado, el
resultado es `None`, nunca un valor fabricado."""

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
    """Extrae el monto inicial de un string de costo (ej. "114.55/mes..." ->
    114.55). Sin número al inicio (ej. "[NO VERIFICADO]"): `None`, nunca 0."""
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
    """Agrega `componente_recomendado` de todas las brechas, deduplicado por
    `nombre_componente`. Licenciamiento + implementación se suman como
    inversión única; infraestructura como costo recurrente mensual."""
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
    """`acciones_organizacionales` consolida `paso_organizacional` de cada
    brecha, deduplicado. `costo_referencia_personal_ti` es el salario mensual
    de referencia (cuánto cuesta 1 puesto, nunca cuántas personas hacen
    falta). El resto son campos del perfil de gobierno ya capturado -- `None`
    si aún no se llenaron, nunca una cifra inventada."""
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
    """Agrupa por si `prerrequisitos` está vacío o no -- no es un grafo de
    dependencias real (es texto libre), solo qué se puede iniciar ya."""
    return {
        "sin_prerrequisitos": [b["variable"] for b in brechas if not b.get("prerrequisitos")],
        "con_prerrequisitos": [b["variable"] for b in brechas if b.get("prerrequisitos")],
    }


# % de `presupuesto_tic_anual` que el costo de UNA acción puede representar
# antes de "presupuesto_extraordinario", por bracket de `poblacion_total`
# (techo inclusive, `None` = sin techo). Calibrable sin tocar la función.
_UMBRAL_PRESUPUESTO_TIC_POR_POBLACION: tuple[tuple[int | None, Decimal], ...] = (
    (20_000, Decimal("0.15")),
    (100_000, Decimal("0.10")),
    (None, Decimal("0.05")),
)


def _umbral_extraordinario(poblacion_total: object) -> Decimal:
    poblacion = poblacion_total if isinstance(poblacion_total, int) else None
    if poblacion is None:
        # Sin dato: el bracket más tolerante evita marcar "extraordinario" sin certeza.
        return _UMBRAL_PRESUPUESTO_TIC_POR_POBLACION[0][1]
    for techo, umbral in _UMBRAL_PRESUPUESTO_TIC_POR_POBLACION:
        if techo is None or poblacion <= techo:
            return umbral
    return _UMBRAL_PRESUPUESTO_TIC_POR_POBLACION[-1][1]


def calcular_factibilidad(brecha: dict, respuestas: dict) -> str:
    """"config_existente" | "presupuesto_extraordinario" | "nueva_norma" --
    sin dato suficiente, cae en "config_existente" (el default menos alarmante).

    Orden: (1) `requiere_nueva_norma` del YAML manda directo a "nueva_norma";
    (2) costo estimado contra `presupuesto_tic_anual`, con el umbral de
    `_umbral_extraordinario` según población; (3) sin componente de costo o
    sin presupuesto capturado, "config_existente"."""
    if brecha.get("requiere_nueva_norma"):
        return "nueva_norma"

    componente = brecha.get("componente_recomendado")
    presupuesto_tic_anual = respuestas.get("presupuesto_tic_anual")
    if componente is None or presupuesto_tic_anual is None:
        return "config_existente"

    costo_licenciamiento = _parsear_monto(componente["costo_licenciamiento"]["moneda_local"])
    costo_implementacion = _parsear_monto(componente["costo_implementacion"]["moneda_local"])
    costo_total = _sumar_opcionales(costo_licenciamiento, costo_implementacion)
    if costo_total is None:
        return "config_existente"

    presupuesto = Decimal(str(presupuesto_tic_anual))
    if presupuesto <= 0:
        return "config_existente"

    if costo_total > presupuesto * _umbral_extraordinario(respuestas.get("poblacion_total")):
        return "presupuesto_extraordinario"
    return "config_existente"


def calcular_progreso_historico(brechas_actuales: list[dict], brechas_anteriores: list[dict]) -> dict:
    """Diff determinista por `variable` entre dos versiones de plan. Se
    computa en lectura, no se persiste."""
    variables_actuales = {b["variable"] for b in brechas_actuales}
    variables_anteriores = {b["variable"] for b in brechas_anteriores}
    return {
        "brechas_resueltas": sorted(variables_anteriores - variables_actuales),
        "brechas_nuevas": sorted(variables_actuales - variables_anteriores),
        "brechas_persistentes": sorted(variables_actuales & variables_anteriores),
    }

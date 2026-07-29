"""Motor de plantillas deterministas (docs/plan-implementacion.md, fase C3): convierte
el catálogo brecha->acción en el `contenido` que vería el funcionario, **sin ningún
LLM**. Es el modo `degradado` de `plan_modernizacion.modo` (docs/backend-schema.md) —
debe producir un plan sustantivo por sí solo, sin ninguna key de API configurada.
"""

from app.engine.reglas_loader import AccionPais, cargar_catalogo, criterio_se_cumple


def _narrativa_plantilla(accion: AccionPais) -> str:
    return (
        f"{accion.paso_administrativo}. {accion.paso_tecnico}. {accion.paso_organizacional}. "
        f"{accion.por_que_importa} (fuente: {accion.fuente_normativa})."
    )


def generar_contenido_degradado(respuestas: dict, pais: str) -> dict:
    """Recorre el catálogo (engine/reglas/*.yaml), evalúa qué brechas aplican para
    estas `respuestas`, y arma el `contenido` con texto de plantilla — nunca decide
    una acción fuera de lo que ya está en el YAML (docs/plan-implementacion.md, E2)."""
    catalogo = cargar_catalogo()
    brechas = []
    for regla in catalogo.values():
        if not criterio_se_cumple(regla.criterio_deteccion, respuestas):
            continue
        if pais not in regla.acciones:
            continue
        accion = regla.acciones[pais]
        brechas.append(
            {
                "variable": regla.variable,
                "categoria_catalogo": accion.categoria_catalogo,
                "paso_administrativo": accion.paso_administrativo,
                "paso_tecnico": accion.paso_tecnico,
                "paso_organizacional": accion.paso_organizacional,
                "prerrequisitos": accion.prerrequisitos,
                "por_que_importa": accion.por_que_importa,
                "fuente_normativa": accion.fuente_normativa,
                "narrativa": _narrativa_plantilla(accion),
            }
        )

    if not brechas:
        # docs/app-flow.md, "Casos especiales": no forzar una recomendación donde no hay brecha real.
        resumen = "No hay brechas pendientes: todas las variables evaluadas ya cumplen el nivel máximo."
    else:
        resumen = f"Se detectaron {len(brechas)} brecha(s) de modernización. Ver detalle de cada una a continuación."

    return {"resumen_narrativo": resumen, "brechas": brechas}

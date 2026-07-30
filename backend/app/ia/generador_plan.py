"""Generador de plan con LLM (docs/plan-implementacion.md, fase E2, F3 en docs/TRD.md).

Ruta usada: `calidad` (Claude, `anthropic/claude-sonnet-4-5` — ver
`app/ia/litellm_config.yaml`), conforme a docs/TRD.md, "Capa de IA — configuración
concreta": "F3 (generador de plan) usa `calidad` (Claude) — la pieza donde la
redacción compleja y la trazabilidad normativa importan más."

Regla dura de docs/plan-implementacion.md, fila E2: este módulo "redacta sobre el
`contenido` ya producido por C2-C3 -- nunca decide la acción, solo la prosa". Por
eso el recorrido del catálogo es idéntico, campo por campo, al de
`app/engine/plantillas.generar_contenido_degradado` -- la única diferencia es cómo
se produce el string `narrativa` de cada brecha. Qué brecha aplica y qué acción le
corresponde lo decide exclusivamente `engine/` (`cargar_catalogo`,
`criterio_se_cumple`), nunca este módulo.

Regla dura de docs/TRD.md ("Estructura de carpetas"): la dependencia entre capas va
en un solo sentido, `ia/` -> `engine/`. Este módulo importa de `app.engine`, nunca
al revés.

Degradación (docs/TRD.md, "Capa de IA"): "Si la API no responde, no hay
conectividad, o la llamada falla por timeout: excepción capturada en `ia/`, cae a
plantilla determinista ... -- nunca un error visible al funcionario." Por eso
`_narrativa_llm` nunca deja escapar una excepción: cualquier fallo (timeout, red,
error de API, respuesta vacía, lo que sea) cae exactamente en
`app.engine.plantillas._narrativa_plantilla`, la misma función que usa el modo
degradado -- se reutiliza tal cual, no se reimplementa.
"""

import litellm

from app.engine.plantillas import _narrativa_plantilla
from app.engine.reglas_loader import AccionPais, cargar_catalogo, criterio_se_cumple
from app.ia.config import api_key_de, esta_disponible, obtener_ruta

# Franja de latencia razonable para una sola llamada de redacción (docs/stack-tecnologico.md,
# benchmark real: API de Claude/DeepSeek del orden de segundos, muy por debajo de este límite).
# El job que invoque este módulo ya es asíncrono (docs/TRD.md, "Job asíncrono -- ciclo de
# vida"), así que este timeout es una protección contra una llamada colgada, no el diseño
# de latencia general del producto.
TIMEOUT_SEGUNDOS = 30

# Nota de diseño: `generar_contenido_llm` hace una llamada a `litellm.completion` por
# cada brecha detectada (no una única llamada para todo el plan) -- así cada narrativa
# se redacta solo a partir de los datos de su propia brecha, evitando que el LLM mezcle
# hechos entre brechas distintas. Para un trámite con varias brechas, la latencia total
# del job es la suma de N llamadas secuenciales (hasta TIMEOUT_SEGUNDOS cada una en el
# peor caso), no una sola llamada de 30-60s -- quien dimensione el timeout del job
# asíncrono (docs/TRD.md, "Job asíncrono") debe considerar N, no 1.
_RUTA_LLM = "calidad"

_PROMPT_INSTRUCCIONES = (
    "Redacta un párrafo breve, profesional y en español neutro, dirigido a un "
    "funcionario municipal, que explique la siguiente acción de modernización. "
    "No inventes hechos, normativa ni pasos que no estén en la información entregada "
    "a continuación -- redacta prosa fluida a partir exclusivamente de estos datos:\n"
    "- Paso administrativo: {paso_administrativo}\n"
    "- Paso técnico: {paso_tecnico}\n"
    "- Paso organizacional: {paso_organizacional}\n"
    "- Por qué importa: {por_que_importa}\n"
    "- Fuente normativa: {fuente_normativa}\n"
    "Devuelve solo el párrafo de prosa, sin encabezados, listas ni texto adicional."
)


def _armar_prompt(accion: AccionPais) -> str:
    return _PROMPT_INSTRUCCIONES.format(
        paso_administrativo=accion.paso_administrativo,
        paso_tecnico=accion.paso_tecnico,
        paso_organizacional=accion.paso_organizacional,
        por_que_importa=accion.por_que_importa,
        fuente_normativa=accion.fuente_normativa,
    )


def _narrativa_llm(accion: AccionPais) -> str:
    """Narrativa de una brecha vía LLM, con fallback obligatorio a la plantilla
    determinista. Nunca lanza una excepción hacia quien llama: ese es precisamente
    el contrato de degradación de docs/TRD.md citado arriba."""
    try:
        ruta = obtener_ruta(_RUTA_LLM)
        api_key = api_key_de(ruta)
        respuesta = litellm.completion(
            model=ruta.model,
            api_key=api_key,
            messages=[{"role": "user", "content": _armar_prompt(accion)}],
            timeout=TIMEOUT_SEGUNDOS,
        )
        # `respuesta` es un `ModelResponse` de LiteLLM; soporta acceso tipo dict
        # (y también en los mocks de test_generador_plan.py, que usan dicts planos).
        narrativa = respuesta["choices"][0]["message"]["content"]
        narrativa = (narrativa or "").strip()
        if not narrativa:
            raise ValueError("Respuesta de LLM vacía")
        return narrativa
    except Exception:
        # Cualquier fallo -- timeout, sin conectividad, error de API, respuesta
        # malformada o vacía -- se captura acá, dentro de `ia/`, y nunca se propaga
        # (docs/TRD.md, "Capa de IA"). Fallback: misma narrativa que usaría el modo
        # degradado para esta brecha.
        return _narrativa_plantilla(accion)


def generar_contenido_llm(respuestas: dict, pais: str) -> dict:
    """Equivalente en forma a `generar_contenido_degradado` (mismo recorrido de
    catálogo, mismos campos por brecha) pero con la `narrativa` de cada brecha
    redactada vía LLM (ruta `calidad`) cuando hay API key configurada, y con
    fallback automático a la plantilla determinista en cualquier otro caso --
    ausencia de key o fallo de la llamada."""
    catalogo = cargar_catalogo()
    brechas = []
    for regla in catalogo.values():
        if not criterio_se_cumple(regla.criterio_deteccion, respuestas):
            continue
        if pais not in regla.acciones:
            continue
        accion = regla.acciones[pais]

        if esta_disponible(_RUTA_LLM):
            narrativa = _narrativa_llm(accion)
        else:
            # Sin API key configurada: ni siquiera se intenta la llamada (docs/TRD.md,
            # `esta_disponible` existe justamente para evitar una llamada que fallaría).
            narrativa = _narrativa_plantilla(accion)

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
                "narrativa": narrativa,
            }
        )

    # Decisión de diseño (E2): el `resumen_narrativo` de nivel de plan se mantiene
    # determinista, igual que en `generar_contenido_degradado`, y NO se redacta vía
    # LLM. Es un mensaje de conteo/estado ("se detectaron N brechas"), no una pieza
    # de redacción compleja con trazabilidad normativa por brecha -- ahí es donde el
    # LLM agrega valor real (principio rector del rol: "los LLM solo donde agregan
    # valor real"). Generarlo vía LLM añadiría una llamada de red y un punto de
    # fallo más por diagnóstico sin mejorar sustantivamente un texto que ya es
    # correcto y suficiente por construcción.
    if not brechas:
        # docs/app-flow.md, "Casos especiales": no forzar una recomendación donde no
        # hay brecha real -- mismo caso especial que en el modo degradado.
        resumen = "No hay brechas pendientes: todas las variables evaluadas ya cumplen el nivel máximo."
    else:
        resumen = f"Se detectaron {len(brechas)} brecha(s) de modernización. Ver detalle de cada una a continuación."

    return {"resumen_narrativo": resumen, "brechas": brechas}

"""Generador de plan con LLM (F3, ruta `calidad`/Claude — docs/TRD.md, "Capa de IA").

Redacta la `narrativa` de cada brecha ya decidida por `engine/` (cargar_catalogo,
criterio_se_cumple) — nunca decide qué brecha aplica ni qué acción le corresponde.
Recorre el catálogo igual que `generar_contenido_degradado`, campo por campo; solo
cambia cómo se produce el string de cada narrativa. `ia/` importa de `engine/`,
nunca al revés.

Cualquier fallo de la ruta `calidad` (timeout, red, API, respuesta vacía) intenta la
ruta de respaldo `calidad_respaldo` (Claude Fable); si esta también falla, cae en
`_narrativa_plantilla`, la misma función que usa el modo degradado.
"""

import litellm

from app.engine.plantillas import _narrativa_plantilla
from app.engine.reglas_loader import AccionPais, cargar_catalogo, criterio_se_cumple
from app.ia.config import api_key_de, esta_disponible, obtener_ruta

TIMEOUT_SEGUNDOS = 30

# Una llamada por brecha (no una sola para todo el plan) evita que el LLM mezcle
# hechos entre brechas distintas.
_RUTA_LLM = "calidad"
# Respaldo de `_RUTA_LLM`: se intenta solo si la llamada a `calidad` falla. Comparte
# la misma API key (`esta_disponible(_RUTA_LLM)` sigue siendo la única puerta).
_RUTA_LLM_RESPALDO = "calidad_respaldo"

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


def _intentar_narrativa_via_ruta(nombre_ruta: str, accion: AccionPais) -> str:
    """Un intento de llamada a `nombre_ruta`. Propaga cualquier excepción hacia quien
    llama (timeout, red, API, respuesta malformada/vacía) -- es responsabilidad de
    `_narrativa_llm` decidir qué hacer con el fallo, esta función no degrada nada."""
    ruta = obtener_ruta(nombre_ruta)
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


def _narrativa_llm(accion: AccionPais) -> str:
    """Narrativa de una brecha vía LLM, con fallback obligatorio a la plantilla
    determinista. Nunca lanza una excepción hacia quien llama: ese es precisamente
    el contrato de degradación de docs/TRD.md citado arriba.

    Cadena de intentos: `calidad` (Claude Sonnet) -> `calidad_respaldo` (Claude
    Fable) -> `_narrativa_plantilla`. Ambas rutas comparten la misma API key, por
    lo que la disponibilidad se decide una sola vez en `generar_contenido_llm`."""
    try:
        return _intentar_narrativa_via_ruta(_RUTA_LLM, accion)
    except Exception:
        pass

    try:
        return _intentar_narrativa_via_ruta(_RUTA_LLM_RESPALDO, accion)
    except Exception:
        # Cualquier fallo de ambas rutas (timeout, red, API, respuesta malformada/
        # vacía) cae en la misma narrativa del modo degradado, nunca se propaga.
        return _narrativa_plantilla(accion)


def generar_contenido_llm(respuestas: dict, pais: str) -> dict:
    """Equivalente en forma a `generar_contenido_degradado` (mismo recorrido de
    catálogo, mismos campos por brecha) pero con la `narrativa` de cada brecha
    redactada vía LLM (ruta `calidad`, con respaldo en `calidad_respaldo`) cuando
    hay API key configurada, y con fallback automático a la plantilla determinista
    en cualquier otro caso -- ausencia de key o fallo de ambas rutas."""
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

    # resumen_narrativo se mantiene determinista (mensaje de conteo/estado, no
    # redacción compleja) — no amerita una llamada LLM adicional.
    if not brechas:
        resumen = "No hay brechas pendientes: todas las variables evaluadas ya cumplen el nivel máximo."
    else:
        resumen = f"Se detectaron {len(brechas)} brecha(s) de modernización. Ver detalle de cada una a continuación."

    return {"resumen_narrativo": resumen, "brechas": brechas}

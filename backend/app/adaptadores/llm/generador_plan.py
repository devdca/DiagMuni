"""Generador de plan con LLM (F3, ruta `calidad`/Claude — docs/TRD.md, "Capa de IA").

Redacta la `narrativa` de cada brecha ya decidida por `engine/` (cargar_catalogo,
criterio_se_cumple) — nunca decide qué brecha aplica ni qué acción le corresponde.
Recorre el catálogo igual que `generar_contenido_degradado`, campo por campo; solo
cambia cómo se produce el string de cada narrativa. `ia/` importa de `engine/`,
nunca al revés.

Cualquier fallo de la ruta `calidad` (timeout, red, API, respuesta vacía) intenta la
ruta de respaldo `calidad_respaldo` (mismo modelo, claude-sonnet-5, desde
2026-09-09 -- protege contra fallos transitorios de una llamada puntual, no
contra un problema a nivel de modelo/generación); si esta también falla, cae en
`_narrativa_plantilla`, la misma función que usa el modo degradado.
"""

import litellm

from app.adaptadores.llm.config import (
    OverrideLlmTenant,
    api_base_de,
    api_key_de,
    esta_disponible,
    obtener_ruta,
    obtener_rutas_generacion,
)
from app.adaptadores.llm.contexto_gobierno import formatear_contexto_gobierno
from app.dominio.catalogo_loader import componente_recomendado_para
from app.dominio.plantillas import _narrativa_plantilla
from app.dominio.reglas_loader import AccionPais, cargar_catalogo, criterio_se_cumple

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
    "{contexto_gobierno}"
    "Devuelve solo el párrafo de prosa, sin encabezados, listas ni texto adicional."
)

_BLOQUE_CONTEXTO_GOBIERNO = (
    "\nContexto real de este gobierno (puedes usarlo para ajustar el tono o "
    "mencionar estas cifras, ej. sugerir un enfoque más gradual si el "
    "presupuesto es bajo -- nunca inventes ninguna cifra que no esté aquí ni "
    "en los datos de arriba):\n{lineas}\n"
)


def _armar_prompt(accion: AccionPais, contexto_gobierno: str) -> str:
    bloque_contexto = _BLOQUE_CONTEXTO_GOBIERNO.format(lineas=contexto_gobierno) if contexto_gobierno else ""
    return _PROMPT_INSTRUCCIONES.format(
        paso_administrativo=accion.paso_administrativo,
        paso_tecnico=accion.paso_tecnico,
        paso_organizacional=accion.paso_organizacional,
        por_que_importa=accion.por_que_importa,
        fuente_normativa=accion.fuente_normativa,
        contexto_gobierno=bloque_contexto,
    )


def _intentar_narrativa_via_ruta(
    nombre_ruta: str, accion: AccionPais, contexto_gobierno: str, *, override: OverrideLlmTenant | None = None
) -> str:
    """Un intento de llamada a `nombre_ruta`. Propaga cualquier excepción hacia quien
    llama (timeout, red, API, respuesta malformada/vacía) -- es responsabilidad de
    `_narrativa_llm` decidir qué hacer con el fallo, esta función no degrada nada."""
    ruta = obtener_ruta(nombre_ruta)
    api_key = api_key_de(ruta, override=override)
    api_base = None
    if api_key is None:
        api_base = api_base_de(ruta, override=override)

    completion_kwargs = {
        "model": ruta.model,
        "messages": [{"role": "user", "content": _armar_prompt(accion, contexto_gobierno)}],
        "timeout": ruta.timeout_segundos,
    }
    if api_key is not None:
        completion_kwargs["api_key"] = api_key
    elif api_base is not None:
        completion_kwargs["api_base"] = api_base

    respuesta = litellm.completion(**completion_kwargs)
    # `respuesta` es un `ModelResponse` de LiteLLM; soporta acceso tipo dict
    # (y también en los mocks de test_generador_plan.py, que usan dicts planos).
    narrativa = respuesta["choices"][0]["message"]["content"]
    narrativa = (narrativa or "").strip()
    if not narrativa:
        raise ValueError("Respuesta de LLM vacía")
    return narrativa


def _narrativa_llm(
    accion: AccionPais, contexto_gobierno: str, *, override: OverrideLlmTenant | None = None
) -> str:
    """Narrativa de una brecha vía LLM, con fallback obligatorio a la plantilla
    determinista. Nunca lanza una excepción hacia quien llama: ese es precisamente
    el contrato de degradación de docs/TRD.md citado arriba.

    Cadena de intentos resuelta por `obtener_rutas_generacion()` (ver
    `app/adaptadores/llm/config.py::obtener_proveedor_llm`): `override` (BYOK, la
    preferencia/credencial propia del tenant) gana sobre `LLM_PROVIDER`; sin
    ninguno de los dos, solo `local` entra por default. Una lista vacía cae
    directo a la plantilla, sin intentar nada.
    """
    for nombre_ruta in obtener_rutas_generacion(override=override):
        if not esta_disponible(nombre_ruta, override=override):
            continue

        try:
            return _intentar_narrativa_via_ruta(nombre_ruta, accion, contexto_gobierno, override=override)
        except Exception:
            pass

    return _narrativa_plantilla(accion)


def generar_contenido_llm(respuestas: dict, pais: str, *, override: OverrideLlmTenant | None = None) -> dict:
    """Equivalente en forma a `generar_contenido_degradado` (mismo recorrido de
    catálogo, mismos campos por brecha) pero con la `narrativa` de cada brecha
    redactada vía LLM (ruta `calidad`, con respaldo en `calidad_respaldo`) cuando
    hay API key configurada (propia del tenant vía `override`, BYOK, o del
    operador), y con fallback automático a la plantilla determinista en
    cualquier otro caso -- ausencia de key o fallo de ambas rutas."""
    catalogo = cargar_catalogo()
    contexto_gobierno = formatear_contexto_gobierno(respuestas, pais)
    brechas = []
    for regla in catalogo.values():
        if not criterio_se_cumple(regla.criterio_deteccion, respuestas):
            continue
        if pais not in regla.acciones:
            continue
        accion = regla.acciones[pais]

        rutas_disponibles = [
            ruta for ruta in obtener_rutas_generacion(override=override) if esta_disponible(ruta, override=override)
        ]
        if rutas_disponibles:
            narrativa = _narrativa_llm(accion, contexto_gobierno, override=override)
        else:
            # Sin ruta de generación disponible: ni siquiera se intenta la llamada.
            # `esta_disponible` existe para evitar una llamada que fallaría.
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
                "componente_recomendado": componente_recomendado_para(accion.categoria_catalogo, pais),
            }
        )

    if not brechas:
        resumen = "No hay brechas pendientes: todas las variables evaluadas ya cumplen el nivel máximo."
    else:
        resumen = f"Se detectaron {len(brechas)} brecha(s) de modernización. Ver detalle de cada una a continuación."

    return {"resumen_narrativo": resumen, "brechas": brechas}

"""Verificador de la salida del generador de plan (F9).

Audita, por cada brecha, que la `narrativa` generada por `generador_plan.py` sea
fiel a los campos estructurados de esa misma brecha en el contenido determinista de
referencia (`generar_contenido_degradado`) — sin inventar normativa, hechos ni
pasos. Nunca decide qué acción corresponde a una brecha, eso ya lo decidió
`engine/`; solo compara texto contra datos, y no importa nada de `engine/`.

Sesgo de fallo fail-closed, a propósito distinto del de `generador_plan.py`: ahí un
fallo del LLM degrada de forma segura a la plantilla (correcta por construcción);
aquí no se puede asumir que el contenido LLM es correcto solo porque no se pudo
confirmar que sea incorrecto, así que cualquier fallo de la llamada/ruta/respuesta
cuenta como "verificación NO aprobada", igual que un "NO" explícito.

Dos capas, en este orden estricto (`verificar_contenido`):
1. **Compuerta determinista** (`verificador_citas.py`, siempre, sin LLM, sin
   costo): rechaza cualquier cita/artículo/plazo mencionado en la narrativa que no
   exista en los datos de referencia. Suficiente por sí sola para `verificado=true`
   en un despliegue sin ninguna API de pago -- el modo `llm` 100% local queda
   completo sin depender de ningún modelo externo.
2. **Veredicto LLM vía `economico`** (DeepSeek, "tarea liviana"; nunca `calidad`
   solo porque ese sea el elegido para redactar), capa opcional adicional que
   suma cobertura semántica más allá de citas/números -- solo si hay
   `DEEPSEEK_API_KEY` configurada, nunca como requisito para aprobar.

`local`/Ollama fue retirado de la cadena de veredicto LLM tras verificación real
(docs/plan-implementacion-e1-bis-capa-ia-local.md sección 9): un modelo pequeño
(phi3, 3.8B) aprobó de forma reproducible (`temperature=0`) una narrativa con un
artículo de ley y un plazo inventados -- no es un bug de formato, es que juzgar
fidelidad factual con un LLM así de chico no es confiable ("suena razonable" no es
lo mismo que "está en los datos"). La compuerta determinista de la capa 1 cubre
exactamente esa clase de error sin necesitar ningún modelo, local o de pago."""

import litellm

from app.ia.config import api_key_de, esta_disponible, obtener_ruta
from app.ia.verificador_citas import citas_y_numeros_son_fieles

_RUTA_VERIFICACION_LLM = "economico"

_PROMPT_INSTRUCCIONES = (
    "Eres un auditor de fidelidad de texto, no un redactor. A continuación se te "
    "entrega una narrativa en prosa y los datos estructurados a partir de los "
    "cuales debió haberse redactado exclusivamente. Tu única tarea es verificar si "
    "la narrativa es fiel a esos datos -- es decir, que NO inventa normativa, "
    "hechos ni pasos que no estén presentes en los datos, y que no los contradice.\n\n"
    "Narrativa a auditar:\n{narrativa}\n\n"
    "Datos estructurados de referencia (la única fuente de verdad permitida):\n"
    "- Paso administrativo: {paso_administrativo}\n"
    "- Paso técnico: {paso_tecnico}\n"
    "- Paso organizacional: {paso_organizacional}\n"
    "- Por qué importa: {por_que_importa}\n"
    "- Fuente normativa: {fuente_normativa}\n\n"
    'Responde ÚNICAMENTE con la palabra "SI" si la narrativa es fiel a los datos, '
    'o ÚNICAMENTE con la palabra "NO" si inventa o contradice algo. No agregues '
    "explicación, puntuación ni ningún otro texto -- tu respuesta debe ser exactamente "
    "una de esas dos palabras."
)


def _armar_prompt(narrativa: str, brecha_determinista: dict) -> str:
    return _PROMPT_INSTRUCCIONES.format(
        narrativa=narrativa,
        paso_administrativo=brecha_determinista["paso_administrativo"],
        paso_tecnico=brecha_determinista["paso_tecnico"],
        paso_organizacional=brecha_determinista["paso_organizacional"],
        por_que_importa=brecha_determinista["por_que_importa"],
        fuente_normativa=brecha_determinista["fuente_normativa"],
    )


def _veredicto_llm(narrativa: str, brecha_determinista: dict) -> bool:
    """Veredicto de UNA brecha vía la ruta `economico` (DeepSeek) -- capa opcional
    adicional de `verificar_contenido`, nunca la única. Fail-closed: cualquier
    fallo o respuesta no reconociblemente "SI" cuenta como rechazo — no hay
    equivalente a la plantilla determinista aquí, porque lo que se evalúa es si se
    puede confiar en el LLM."""
    try:
        ruta = obtener_ruta(_RUTA_VERIFICACION_LLM)
        api_key = api_key_de(ruta)

        completion_kwargs = {
            "model": ruta.model,
            "messages": [{"role": "user", "content": _armar_prompt(narrativa, brecha_determinista)}],
            "timeout": ruta.timeout_segundos,
            "api_key": api_key,
            # Tarea de clasificación binaria (sí/no), no redacción -- a diferencia
            # de F3 (generador_plan.py, que sí necesita variabilidad de prosa y no
            # fija estos parámetros). `temperature=0` hace el veredicto reproducible;
            # `max_tokens=10` acota el costo de cualquier divagación sin arriesgar
            # truncar "SI"/"SÍ"/"NO".
            "temperature": 0,
            "max_tokens": 10,
            # Sin esto, un modelo en modo de completado crudo puede responder bien
            # ("SI") pero seguir alucinando un turno nuevo después (confirmado con
            # `ollama/phi3` en verificación real de G4: 'SI\n\n\n### User:\nE...',
            # antes de que `local` se retirara de esta capa -- ver docstring del
            # módulo) -- cortar en el primer salto de línea descarta esa
            # alucinación sin arriesgar la palabra válida.
            "stop": ["\n"],
        }

        respuesta = litellm.completion(**completion_kwargs)
        veredicto = respuesta["choices"][0]["message"]["content"]
        # Normaliza puntuación/comillas/énfasis envolventes ("SI.", '"SÍ"', "**SI**")
        # antes de exigir igualdad exacta del resto -- pero NUNCA prefix-match:
        # "SIN EMBARGO..." y "SI BIEN LA NARRATIVA CONTRADICE..." son aperturas
        # concesivas comunes en español que un prefix-match aprobaría por error.
        veredicto = (veredicto or "").strip().strip(".,;:!¡\"'*() \t\n").upper()
        # Solo un "SI" (o "SÍ") inequívoco cuenta como aprobado -- cualquier otra
        # cosa (vacío, "NO", prosa que no sigue la instrucción, etc.) es rechazo.
        return veredicto in ("SI", "SÍ")
    except Exception:
        return False


def verificar_contenido(contenido_llm: dict, contenido_determinista: dict) -> bool:
    """True solo si CADA brecha de `contenido_llm` pasa las dos capas de F9, en
    este orden estricto (ver docstring del módulo):
    1. Compuerta determinista (`verificador_citas.py`, siempre) -- basta ella sola
       para aprobar si no hay ninguna API de pago configurada.
    2. Veredicto LLM vía `economico`, solo si hay `DEEPSEEK_API_KEY` -- capa
       adicional, nunca sustituye a la compuerta ni es requisito para aprobar sin
       ella.

    False ante cualquier discrepancia estructural (cantidad de brechas, variable
    sin contraparte), cualquier cita/número no encontrado en la referencia, o
    cualquier veredicto LLM fallido cuando esa capa sí corre. Solo audita — quien
    invoca decide qué hacer con el resultado."""
    brechas_llm = contenido_llm.get("brechas", [])
    brechas_deterministas = {b["variable"]: b for b in contenido_determinista.get("brechas", [])}

    if len(brechas_llm) != len(brechas_deterministas):
        return False

    hay_llm_disponible = esta_disponible(_RUTA_VERIFICACION_LLM)

    for brecha in brechas_llm:
        referencia = brechas_deterministas.get(brecha.get("variable"))
        if referencia is None:
            return False

        narrativa = brecha.get("narrativa", "")
        if not citas_y_numeros_son_fieles(narrativa, referencia):
            return False
        if hay_llm_disponible and not _veredicto_llm(narrativa, referencia):
            return False

    return True

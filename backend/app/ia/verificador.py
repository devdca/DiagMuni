"""Verificador de la salida del generador de plan (F9, ruta `economico`/DeepSeek).

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
"""

import litellm

from app.ia.config import api_key_de, esta_disponible, obtener_ruta

TIMEOUT_SEGUNDOS = 15

_RUTA_LLM = "economico"

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
    """Veredicto de UNA brecha vía LLM. Fail-closed: cualquier fallo o respuesta no
    reconociblemente "SI" cuenta como rechazo — no hay equivalente a la plantilla
    determinista aquí, porque lo que se evalúa es si se puede confiar en el LLM."""
    try:
        ruta = obtener_ruta(_RUTA_LLM)
        api_key = api_key_de(ruta)
        respuesta = litellm.completion(
            model=ruta.model,
            api_key=api_key,
            messages=[{"role": "user", "content": _armar_prompt(narrativa, brecha_determinista)}],
            timeout=TIMEOUT_SEGUNDOS,
        )
        veredicto = respuesta["choices"][0]["message"]["content"]
        veredicto = (veredicto or "").strip().upper()
        # Solo un "SI" (o "SÍ") inequívoco cuenta como aprobado -- cualquier otra
        # cosa (vacío, "NO", prosa que no sigue la instrucción, etc.) es rechazo.
        return veredicto in ("SI", "SÍ")
    except Exception:
        return False


def verificar_contenido(contenido_llm: dict, contenido_determinista: dict) -> bool:
    """True solo si CADA brecha de `contenido_llm` tiene una narrativa auditada y
    aprobada contra la brecha correspondiente (misma `variable`) en
    `contenido_determinista`. False en cualquier otro caso: ruta no disponible,
    discrepancia estructural entre ambos contenidos, o cualquier veredicto fallido.
    Solo audita — quien invoca decide qué hacer con el resultado."""
    if not esta_disponible(_RUTA_LLM):
        return False

    brechas_llm = contenido_llm.get("brechas", [])
    brechas_deterministas = {b["variable"]: b for b in contenido_determinista.get("brechas", [])}

    if len(brechas_llm) != len(brechas_deterministas):
        return False

    for brecha in brechas_llm:
        referencia = brechas_deterministas.get(brecha.get("variable"))
        if referencia is None:
            return False
        if not _veredicto_llm(brecha.get("narrativa", ""), referencia):
            return False

    return True

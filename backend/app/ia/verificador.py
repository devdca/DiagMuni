"""Verificador de la salida del generador de plan (docs/plan-implementacion.md, fase
E3, F9 en docs/TRD.md).

Fuente exacta de la regla (docs/plan-implementacion.md, fila E3): "Verificador
(F9): audita la salida de E2 contra el `contenido` estructurado antes de marcar
`verificado=true`; si falla, el plan se muestra en modo degradado (fase C), nunca
sin verificar."

Ruta usada: `economico` (DeepSeek), conforme a docs/TRD.md, "Capa de IA —
configuración concreta": "F9 (verificador) usa `economico` (DeepSeek) — solo
compara la salida de F3 contra la estructura de `engine/`, tarea liviana." Por eso
este módulo pide un veredicto (SI/NO), no prosa: es una tarea de auditoría/
comparación, no de redacción -- no necesita la ruta `calidad`.

Qué audita: por cada brecha del contenido generado por `generador_plan.py`
(`app.ia.generador_plan.generar_contenido_llm`), que su `narrativa` sea fiel
exclusivamente a los campos estructurados de esa misma brecha en el contenido
determinista de referencia (`app.engine.plantillas.generar_contenido_degradado`)
-- que no invente normativa, hechos ni pasos que no estén en
`paso_administrativo`/`paso_tecnico`/`paso_organizacional`/`por_que_importa`/
`fuente_normativa`. Nunca decide qué acción corresponde a una brecha -- eso ya lo
decidió `engine/` antes de que este módulo exista; solo compara texto contra datos.

Regla dura de docs/TRD.md ("Estructura de carpetas"): la dependencia entre capas va
en un solo sentido, `ia/` -> `engine/`. Este módulo no importa nada de `app.engine`
--recibe ambos contenidos (LLM y determinista) ya armados por quien lo invoca
(`app/jobs/plan_job.py`), así que ni siquiera necesita esa dependencia.

Sesgo de fallo -- el punto de diseño más importante de este módulo, y lo que lo
distingue de `generador_plan.py`: en generación (E2), un fallo del LLM degrada de
forma segura a la plantilla determinista, porque esa plantilla es correcta por
construcción. En verificación (E3) el razonamiento es distinto: si la llamada de
auditoría falla, no está disponible, da timeout, o devuelve algo no parseable, NO
se puede asumir que el contenido LLM es correcto solo porque no se pudo confirmar
que sea incorrecto. Por eso este módulo nunca asume éxito por defecto -- cualquier
fallo (de la llamada, de la ruta, de la respuesta) se trata como "verificación NO
aprobada", igual de estricto que un "NO" explícito del LLM. Quien invoque este
módulo (`app/jobs/plan_job.py`) descarta el contenido LLM y persiste el contenido
determinista en cualquiera de los dos casos -- pero por razones distintas, que el
código de este módulo no debe ocultar (ver docstring de `app/jobs/plan_job.py`)."""

import litellm

from app.ia.config import api_key_de, esta_disponible, obtener_ruta

# Franja de latencia razonable para una sola llamada de auditoría -- más corta que
# el timeout de redacción de generador_plan.py (30s) porque un veredicto SI/NO es
# una tarea liviana (docs/TRD.md, "tarea liviana"), no redacción de prosa.
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
    """Veredicto de UNA brecha vía LLM (ruta `economico`). Fail-closed: cualquier
    fallo -- timeout, sin conectividad, error de API, respuesta vacía, o una
    respuesta que no sea reconociblemente "SI" -- se trata como verificación NO
    aprobada. Nunca deja escapar una excepción hacia quien la invoca (mismo patrón
    defensivo que `_narrativa_llm` en `generador_plan.py`), pero, a diferencia de
    esa función, nunca "recupera" un resultado utilizable en el camino de fallo --
    no existe aquí un equivalente seguro a la plantilla determinista de E2, porque
    lo que se está evaluando es precisamente si se puede confiar en el texto LLM."""
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
    aprobada contra los datos estructurados de la brecha correspondiente (misma
    `variable`) en `contenido_determinista`. False en cualquier otro caso --
    incluyendo que la ruta `economico` no esté disponible, que el número de brechas
    o las variables no coincidan entre ambos contenidos (discrepancia estructural,
    tratada igual de estricta que una narrativa infiel), o que cualquier veredicto
    individual falle o no se pueda obtener.

    Quien invoca esta función (`app/jobs/plan_job.py`) es responsable de decidir
    qué hacer con el resultado (persistir el contenido LLM si es True, descartarlo
    y usar el determinista si es False) -- este módulo solo audita, no decide modo
    ni persiste nada (docs/plan-implementacion.md, fila E3)."""
    if not esta_disponible(_RUTA_LLM):
        # Sin key configurada para `economico`: ni siquiera se intenta la llamada
        # (mismo principio que `esta_disponible` en generador_plan.py) -- y, a
        # diferencia de E2, la ausencia de verificador no puede leerse como "está
        # bien, sigue adelante": es "no se pudo verificar", que cuenta como False.
        return False

    brechas_llm = contenido_llm.get("brechas", [])
    brechas_deterministas = {b["variable"]: b for b in contenido_determinista.get("brechas", [])}

    if len(brechas_llm) != len(brechas_deterministas):
        return False

    for brecha in brechas_llm:
        referencia = brechas_deterministas.get(brecha.get("variable"))
        if referencia is None:
            # La brecha del contenido LLM no tiene contraparte determinista con la
            # misma variable -- discrepancia estructural, no se puede auditar.
            return False
        if not _veredicto_llm(brecha.get("narrativa", ""), referencia):
            return False

    return True

"""Verificador de la salida del generador de plan (F9): audita que la `narrativa`
sea fiel a los datos estructurados de esa brecha, sin inventar normativa/hechos.
No decide acciones, solo compara texto contra datos.

Fail-closed (a diferencia de `generador_plan.py`, que degrada a plantilla): un
fallo de la llamada/ruta/respuesta cuenta como "NO aprobada".

Dos capas en orden estricto (`verificar_contenido`): (1) compuerta determinista
(`verificador_citas.py`, siempre, sin LLM/costo) -- basta sola para `verificado=true`
sin ninguna API de pago; (2) veredicto LLM vía `economico`, capa opcional que suma
cobertura semántica, solo si hay `DEEPSEEK_API_KEY`, nunca requisito.

`local`/Ollama se retiró del veredicto (docs/plan-implementacion-e1-bis-capa-ia-local.md
sección 9): un modelo chico (phi3) aprobó de forma reproducible una narrativa con
normativa inventada -- juzgar fidelidad factual con un LLM así de chico no es
confiable. La compuerta determinista cubre esa clase de error sin necesitar modelo."""

import litellm

from app.adaptadores.llm.config import OverrideLlmTenant, api_key_de, esta_disponible, obtener_ruta
from app.adaptadores.llm.verificador_citas import citas_y_numeros_son_fieles

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
    "- Fuente normativa: {fuente_normativa}\n"
    "{contexto_gobierno}\n"
    'Responde ÚNICAMENTE con la palabra "SI" si la narrativa es fiel a los datos, '
    'o ÚNICAMENTE con la palabra "NO" si inventa o contradice algo. No agregues '
    "explicación, puntuación ni ningún otro texto -- tu respuesta debe ser exactamente "
    "una de esas dos palabras."
)

_BLOQUE_CONTEXTO_GOBIERNO = (
    "\nContexto real del gobierno (también es fuente de verdad válida -- una "
    "cifra de aquí NO cuenta como inventada):\n{lineas}\n"
)


def _armar_prompt(narrativa: str, brecha_determinista: dict, contexto_gobierno: str = "") -> str:
    bloque_contexto = _BLOQUE_CONTEXTO_GOBIERNO.format(lineas=contexto_gobierno) if contexto_gobierno else ""
    return _PROMPT_INSTRUCCIONES.format(
        narrativa=narrativa,
        paso_administrativo=brecha_determinista["paso_administrativo"],
        paso_tecnico=brecha_determinista["paso_tecnico"],
        paso_organizacional=brecha_determinista["paso_organizacional"],
        por_que_importa=brecha_determinista["por_que_importa"],
        fuente_normativa=brecha_determinista["fuente_normativa"],
        contexto_gobierno=bloque_contexto,
    )


def _veredicto_llm(
    narrativa: str,
    brecha_determinista: dict,
    contexto_gobierno: str = "",
    *,
    override: OverrideLlmTenant | None = None,
) -> bool:
    """Veredicto de UNA brecha vía `economico` -- capa opcional, nunca la única.
    Fail-closed: cualquier fallo o respuesta que no sea "SI" inequívoco es rechazo.
    `override` (BYOK): ver app/aplicacion/preferencia_modelo_ia.py::resolver_override."""
    try:
        ruta = obtener_ruta(_RUTA_VERIFICACION_LLM)
        api_key = api_key_de(ruta, override=override)

        completion_kwargs = {
            "model": ruta.model,
            "messages": [
                {"role": "user", "content": _armar_prompt(narrativa, brecha_determinista, contexto_gobierno)}
            ],
            "timeout": ruta.timeout_segundos,
            "api_key": api_key,
            # Clasificación binaria, no redacción: temperature=0 (reproducible),
            # max_tokens=10 (acota costo sin truncar "SI"/"SÍ"/"NO").
            "temperature": 0,
            "max_tokens": 10,
            # Corta en el primer salto de línea -- sin esto un modelo puede acertar
            # "SI" y seguir alucinando texto después.
            "stop": ["\n"],
            # deepseek-v4-pro razona por default; sin desactivarlo la respuesta
            # llega vacía o tarda de más gastando tokens en pensar antes de "SI"/"NO".
            "extra_body": {"thinking": {"type": "disabled"}},
        }

        respuesta = litellm.completion(**completion_kwargs)
        veredicto = respuesta["choices"][0]["message"]["content"]
        # Normaliza puntuación envolvente, pero nunca prefix-match: aperturas
        # concesivas como "SIN EMBARGO..." lo aprobarían por error.
        veredicto = (veredicto or "").strip().strip(".,;:!¡\"'*() \t\n").upper()
        return veredicto in ("SI", "SÍ")
    except Exception:
        return False


def verificar_contenido(
    contenido_llm: dict,
    contenido_determinista: dict,
    contexto_gobierno: str = "",
    *,
    override: OverrideLlmTenant | None = None,
) -> bool:
    """True solo si CADA brecha pasa las dos capas de F9 (ver docstring del
    módulo): compuerta determinista siempre, veredicto LLM solo si hay
    `DEEPSEEK_API_KEY`. Solo audita -- quien invoca decide qué hacer con el resultado."""
    brechas_llm = contenido_llm.get("brechas", [])
    brechas_deterministas = {b["variable"]: b for b in contenido_determinista.get("brechas", [])}

    if len(brechas_llm) != len(brechas_deterministas):
        return False

    hay_llm_disponible = esta_disponible(_RUTA_VERIFICACION_LLM, override=override)

    for brecha in brechas_llm:
        referencia = brechas_deterministas.get(brecha.get("variable"))
        if referencia is None:
            return False

        narrativa = brecha.get("narrativa", "")
        if not citas_y_numeros_son_fieles(narrativa, referencia, contexto_gobierno):
            return False
        if hay_llm_disponible and not _veredicto_llm(narrativa, referencia, contexto_gobierno, override=override):
            return False

    return True

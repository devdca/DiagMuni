"""Asistente de captura F1 (docs/plan-implementacion.md, fase E4; F1 en docs/TRD.md
línea 93). Diseño aprobado, fuente de verdad de este módulo:
`entregables/fase-2/asistente-captura-f1.md`, secciones 2.2, 2.3 y 4 -- este código
implementa ese diseño tal cual, sin re-decidir nada de lo ya resuelto ahí.

Ruta usada: `economico` (DeepSeek), conforme a docs/TRD.md línea 93: "F1 (asistente
de captura, clasificación de texto libre) usa `economico` (DeepSeek)". Mismo tipo de
tarea que F9 (`verificador.py`): la salida esperada es una etiqueta corta de una
lista fija de categorías, no prosa -- no hay razón para usar `calidad` aquí
(asistente-captura-f1.md, sección 4).

Qué hace: dos funciones de clasificación de texto libre (la "aclaración" que el
funcionario puede escribir junto a cada pregunta del cuestionario F1,
asistente-captura-f1.md sección 1).

(A) `clasificar_consistencia_booleana`: dado el texto de la aclaración y el valor
booleano que el funcionario ya marcó para una de las 5 variables booleanas del
catálogo (`documentos_digitalizados`, `motor_pagos`, `firma_electronica_habilitada`,
`interoperabilidad`, `proteccion_datos_incompleta`), clasifica si el texto parece
contradecir ese valor. Nunca decide el valor final -- solo sugiere, y la
confirmación humana (fase F, frontend) es lo único que puede cambiar la variable
(asistente-captura-f1.md, sección 2.2, "Mecanismo de confirmación").

(B) `clasificar_mecanismo_identidad`: dado el texto que el funcionario escribió al
elegir "Otro, especifique" en `mecanismo_identidad`, clasifica el texto en una de
las 4 categorías canónicas del catálogo (`llave_mx`, `id_uruguay`, `propio`,
`ninguno`) o en `no_clasificable`. Las candidatas `llave_mx`/`id_uruguay` se
restringen por país (`llave_mx` solo si `pais == "mx"`, `id_uruguay` solo si
`pais == "uy"`) tanto en la construcción del prompt (nunca se le ofrece al LLM la
categoría del país contrario) como en la validación de la respuesta (si el LLM la
devuelve de todos modos, se invalida y cae a `no_clasificable`) -- doble barrera,
igual que exige asistente-captura-f1.md sección 2.2: "nunca se le ofrece a un
tenant mexicano 'id_uruguay' como clasificación posible, ni viceversa".

Regla dura preservada (igual que E2/E3, asistente-captura-f1.md sección 2.2,
"Relación con la regla dura del proyecto"): este módulo nunca decide el índice de
madurez ni una acción del plan, nunca escribe en `engine/` (no importa nada de
`app.engine`, igual que `verificador.py`), y nunca persiste nada por sí solo --
solo devuelve una etiqueta. La persistencia con confirmación humana es un
mecanismo de UI (fase F), completamente fuera del alcance de este módulo backend.

Sesgo de fallo -- LO OPUESTO al de `verificador.py` (E3), y es el punto de diseño
más importante de este módulo (asistente-captura-f1.md, sección 2.3): en E3
(fail-CLOSED), cualquier fallo de la llamada de auditoría se trata como
"verificación NO aprobada" -- rechazo estricto, porque no se puede asumir que un
contenido es correcto solo porque no se pudo confirmar que sea incorrecto. Aquí el
razonamiento es el inverso: el sesgo correcto es "no sugerir nada", nunca
"rechazar" nada. Cualquier fallo -- timeout, sin conectividad, ruta `economico` no
disponible (`esta_disponible` devuelve False), respuesta no reconocible o no
parseable a una de las categorías válidas -- devuelve el resultado fail-safe de
cada función (`no_concluyente` / `no_clasificable`). Esto es exactamente lo que
haría el sistema si esta clasificación no existiera: la aclaración queda solo como
texto de apoyo sin clasificar (rol 2.1 del diseño), nunca bloquea nada. Por eso
ninguna función de este módulo deja escapar una excepción -- ni una sola llamada
puede convertirse en un error visible al funcionario ni en un bloqueo del
cuestionario.

Latencia: `TIMEOUT_SEGUNDOS = 15`, idéntico al de `verificador.py` (llamada
síncrona de vida corta, no un job asíncrono -- asistente-captura-f1.md sección 3,
"no debería requerir una nueva entrada en el enum `job.tipo`").
"""

import litellm

from app.ia.config import api_key_de, esta_disponible, obtener_ruta

# Franja de latencia razonable para una sola llamada de clasificación -- idéntica a
# la de `verificador.py` (F9), no a la de `generador_plan.py` (F3, 30s dentro de un
# job asíncrono): esta es una llamada síncrona de vida corta, análoga en perfil de
# latencia a un veredicto SI/NO, no a redacción de prosa (asistente-captura-f1.md,
# sección 4, y sección 3 sobre el perfil de latencia).
TIMEOUT_SEGUNDOS = 15

_RUTA_LLM = "economico"

# --- (A) Consistencia de las 5 variables booleanas -------------------------------

CONSISTENTE = "consistente"
POSIBLE_CONTRADICCION_HACIA_SI = "posible_contradiccion_hacia_si"
POSIBLE_CONTRADICCION_HACIA_NO = "posible_contradiccion_hacia_no"
NO_CONCLUYENTE = "no_concluyente"

_CATEGORIAS_CONSISTENCIA = {
    CONSISTENTE,
    POSIBLE_CONTRADICCION_HACIA_SI,
    POSIBLE_CONTRADICCION_HACIA_NO,
    NO_CONCLUYENTE,
}

_PROMPT_CONSISTENCIA = (
    "Eres un clasificador de consistencia, no un redactor. Un funcionario municipal "
    "marcó un valor de Sí/No para una pregunta de un cuestionario, y además escribió "
    "una aclaración de texto libre para esa misma pregunta. Tu única tarea es "
    "clasificar si la aclaración contradice el valor marcado.\n\n"
    "Valor marcado por el funcionario: {valor_marcado}\n"
    "Aclaración escrita por el funcionario:\n{texto_aclaracion}\n\n"
    "Responde ÚNICAMENTE con una de estas cuatro palabras, exactamente como se "
    "escriben, sin puntuación ni texto adicional:\n"
    '- "consistente": la aclaración no contradice el valor marcado.\n'
    '- "posible_contradiccion_hacia_si": la aclaración sugiere que el valor real es '
    'Sí, pero el funcionario marcó No.\n'
    '- "posible_contradiccion_hacia_no": la aclaración sugiere que el valor real es '
    'No, pero el funcionario marcó Sí.\n'
    '- "no_concluyente": la aclaración es ambigua y no permite determinar si '
    "contradice o no el valor marcado."
)


def _armar_prompt_consistencia(texto_aclaracion: str, valor_marcado: bool) -> str:
    return _PROMPT_CONSISTENCIA.format(
        valor_marcado="Sí" if valor_marcado else "No",
        texto_aclaracion=texto_aclaracion,
    )


def clasificar_consistencia_booleana(texto_aclaracion: str, valor_marcado: bool) -> str:
    """Clasifica si `texto_aclaracion` contradice `valor_marcado` (el booleano que
    el funcionario ya marcó para una de las 5 variables booleanas del catálogo --
    `documentos_digitalizados`, `motor_pagos`, `firma_electronica_habilitada`,
    `interoperabilidad`, `proteccion_datos_incompleta`). Devuelve una de las 4
    categorías fijas del diseño (asistente-captura-f1.md, sección 2.2).

    Fail-safe hacia `no_concluyente` -- NO fail-closed como `verificador.py`: aquí
    "no se pudo clasificar" y "el texto es ambiguo" tienen el mismo resultado
    seguro, porque ambos casos significan lo mismo para quien invoca esta función --
    no sugerir nada (asistente-captura-f1.md, sección 2.3). Esto cubre: ruta
    `economico` no disponible, cualquier excepción de la llamada (timeout, sin
    conectividad, error de API), respuesta vacía, o una respuesta que no sea
    reconociblemente una de las 4 categorías válidas. Nunca deja escapar una
    excepción hacia quien la invoca."""
    if not esta_disponible(_RUTA_LLM):
        return NO_CONCLUYENTE

    try:
        ruta = obtener_ruta(_RUTA_LLM)
        api_key = api_key_de(ruta)
        respuesta = litellm.completion(
            model=ruta.model,
            api_key=api_key,
            messages=[
                {
                    "role": "user",
                    "content": _armar_prompt_consistencia(texto_aclaracion, valor_marcado),
                }
            ],
            timeout=TIMEOUT_SEGUNDOS,
        )
        categoria = respuesta["choices"][0]["message"]["content"]
        categoria = (categoria or "").strip().lower()
        if categoria in _CATEGORIAS_CONSISTENCIA:
            return categoria
        # Respuesta no reconocible -- mismo fail-safe que cualquier otro fallo.
        return NO_CONCLUYENTE
    except Exception:
        return NO_CONCLUYENTE


# --- (B) Clasificación de mecanismo_identidad ("Otro, especifique") --------------

LLAVE_MX = "llave_mx"
ID_URUGUAY = "id_uruguay"
PROPIO = "propio"
NINGUNO = "ninguno"
NO_CLASIFICABLE = "no_clasificable"

_CATEGORIAS_BASE = {PROPIO, NINGUNO}

_PROMPT_MECANISMO_IDENTIDAD = (
    "Eres un clasificador de texto, no un redactor. Un funcionario de un gobierno "
    "municipal eligió la opción 'Otro, especifique' al describir el mecanismo de "
    "identidad digital/acceso que usa su trámite, y escribió el siguiente texto "
    "libre. Tu única tarea es clasificar ese texto en una de las categorías "
    "permitidas a continuación.\n\n"
    "Texto escrito por el funcionario:\n{texto_aclaracion}\n\n"
    "Categorías permitidas (usa EXACTAMENTE una de estas palabras, sin puntuación "
    "ni texto adicional):\n"
    "{categorias_disponibles}\n"
    '- "no_clasificable": el texto no permite determinar con confianza cuál de las '
    "categorías anteriores corresponde."
)

_DESCRIPCION_CATEGORIA = {
    LLAVE_MX: (
        '"llave_mx": el texto describe el mecanismo de identidad digital nacional '
        "de México (Llave MX)."
    ),
    ID_URUGUAY: (
        '"id_uruguay": el texto describe el mecanismo de identidad digital nacional '
        "de Uruguay (ID Uruguay)."
    ),
    PROPIO: (
        '"propio": el texto describe un mecanismo de identidad/acceso propio de ese '
        "gobierno municipal/departamental, no un mecanismo nacional."
    ),
    NINGUNO: '"ninguno": el texto indica que no existe ningún mecanismo de identidad/acceso.',
}


def _categorias_candidatas(pais: str) -> set[str]:
    """Restricción de candidatas por país (asistente-captura-f1.md, sección 2.2):
    `llave_mx` SOLO si `pais == "mx"`, `id_uruguay` SOLO si `pais == "uy"` -- nunca
    se le ofrece a un tenant la categoría del país contrario. Esta función es la
    primera de las dos barreras (la segunda es la validación de la respuesta en
    `clasificar_mecanismo_identidad`)."""
    candidatas = set(_CATEGORIAS_BASE)
    if pais == "mx":
        candidatas.add(LLAVE_MX)
    elif pais == "uy":
        candidatas.add(ID_URUGUAY)
    return candidatas


def _armar_prompt_mecanismo_identidad(texto_aclaracion: str, pais: str) -> str:
    candidatas = _categorias_candidatas(pais)
    # Orden estable para que el prompt sea determinista y reproducible en tests.
    descripciones = [
        _DESCRIPCION_CATEGORIA[categoria]
        for categoria in (LLAVE_MX, ID_URUGUAY, PROPIO, NINGUNO)
        if categoria in candidatas
    ]
    return _PROMPT_MECANISMO_IDENTIDAD.format(
        texto_aclaracion=texto_aclaracion,
        categorias_disponibles="\n".join(descripciones),
    )


def clasificar_mecanismo_identidad(texto_aclaracion: str, pais: str) -> str:
    """Clasifica `texto_aclaracion` (escrito tras elegir "Otro, especifique" en
    `mecanismo_identidad`) en una de: `llave_mx`, `id_uruguay`, `propio`, `ninguno`,
    o `no_clasificable`. `pais` es `"mx"` o `"uy"` (mismo particionamiento que ya
    usa el catálogo determinista, `backend/app/engine/reglas/*.yaml`).

    Restricción de candidatas por país, con doble barrera (asistente-captura-f1.md,
    sección 2.2): (1) el prompt nunca ofrece al LLM la categoría del país contrario
    (`_categorias_candidatas`/`_armar_prompt_mecanismo_identidad`); (2) aunque el
    LLM devolviera de todos modos esa categoría por error de prompt, la validación
    de abajo la invalida y cae a `no_clasificable` -- nunca es posible que esta
    función devuelva `llave_mx` para `pais="uy"` ni `id_uruguay` para `pais="mx"`.

    Fail-safe hacia `no_clasificable` -- NO fail-closed: ruta no disponible,
    cualquier excepción de la llamada, respuesta vacía, respuesta no reconocible, o
    respuesta que sea una categoría válida pero no candidata para este país, caen
    todas en `no_clasificable`. Nunca deja escapar una excepción."""
    if not esta_disponible(_RUTA_LLM):
        return NO_CLASIFICABLE

    candidatas = _categorias_candidatas(pais)

    try:
        ruta = obtener_ruta(_RUTA_LLM)
        api_key = api_key_de(ruta)
        respuesta = litellm.completion(
            model=ruta.model,
            api_key=api_key,
            messages=[
                {
                    "role": "user",
                    "content": _armar_prompt_mecanismo_identidad(texto_aclaracion, pais),
                }
            ],
            timeout=TIMEOUT_SEGUNDOS,
        )
        categoria = respuesta["choices"][0]["message"]["content"]
        categoria = (categoria or "").strip().lower()
        if categoria in candidatas:
            return categoria
        # No reconocible, o reconocible pero no candidata para este país (ej. el
        # LLM devolvió `id_uruguay` para un tenant mexicano) -- segunda barrera de
        # la restricción por país, mismo fail-safe que cualquier otro fallo.
        return NO_CLASIFICABLE
    except Exception:
        return NO_CLASIFICABLE

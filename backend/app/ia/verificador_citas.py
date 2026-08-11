"""Compuerta determinista de F9 -- sin LLM, sin API, sin costo. Corre siempre,
antes que cualquier veredicto de `verificador.py` (nunca al revés): si esta
compuerta rechaza, no importa qué diría un LLM, la narrativa queda rechazada.

Motivación real (docs/plan-implementacion-e1-bis-capa-ia-local.md sección 9): un
modelo local pequeño (phi3, 3.8B) aprobó de forma reproducible una narrativa con
un artículo de ley y un plazo inventados -- no por un bug de formato, sino porque
juzgar fidelidad factual con un LLM chico no es confiable ("suena razonable" no es
lo mismo que "está en los datos"). Esta compuerta no reemplaza ese juicio semántico
-- lo evita por completo para la clase de error más grave y más verificable
mecánicamente: una cita normativa, un artículo o un plazo que el texto generado
menciona pero que no existe en ninguno de los campos estructurados de origen.

Qué SÍ detecta, determinísticamente: números de artículo/decreto inventados,
acrónimos de ley inventados o equivocados, y cantidades de tiempo (días/meses/
años/horas) inventadas.

Qué NO detecta -- limitación real, no ocultarla: tergiversación del CONTENIDO de
una cita que sí existe en los datos (ej. atribuirle a una ley real una excepción
que no otorga), o una contradicción que no introduce ningún número ni nombre de
norma nuevo. Es una mejora estricta sobre no tener ningún chequeo mecánico, no una
auditoría semántica completa -- ver `verificador.py` para la capa LLM opcional que
cubre (sin garantía) esas clases más sutiles cuando hay una API de pago disponible.

No importa nada de `engine/` (mismo contrato que `verificador.py`): solo compara
texto contra texto, nunca decide qué acción corresponde a una brecha.
"""

import re
import unicodedata

_CAMPOS_REFERENCIA = (
    "paso_administrativo",
    "paso_tecnico",
    "paso_organizacional",
    "por_que_importa",
    "fuente_normativa",
)

# Números de artículo/decreto: capturan solo el identificador (dígitos + sufijo
# tipo "-III"/"bis"), nunca la palabra "artículo"/"art." que lo precede -- así el
# chequeo es robusto a que la narrativa reformule "art. 25-III" como "artículo
# 25, fracción III" (mismo identificador numérico, prefijo distinto).
_PATRON_NUM_ARTICULO = re.compile(r"art(?:[íi]culo)?s?\.?\s*(\d+[a-z]*(?:[\-/]\w+)?)", re.IGNORECASE)
_PATRON_NUM_DECRETO = re.compile(
    r"decreto\s*(?:n[uú]m(?:ero)?\.?)?\s*(\d+[a-z]*(?:[\-/]\w+)?)", re.IGNORECASE
)
# Cantidades de tiempo -- el vector concreto que motivó este módulo ("10 días
# naturales" inventado). Un número suelto sin unidad (ej. "índice 2 a 3") no
# cuenta -- eso no es una afirmación normativa verificable, es parte del texto
# libre y generaría demasiados falsos rechazos.
_PATRON_NUMERO_CON_UNIDAD = re.compile(r"(\d+\s*(?:d[ií]as?|mes(?:es)?|a[ñn]os?|horas?))", re.IGNORECASE)
# Acrónimos de 3+ mayúsculas (LNETB, LFEA, LGPDPPSO, ATDT, SAT...) -- proteger
# contra un acrónimo inventado o equivocado (ej. el caso ya documentado de olmo2
# confundiendo SAT con otra sigla, docs/stack-tecnologico.md).
_PATRON_ACRONIMO = re.compile(r"\b[A-ZÑ]{3,}\b")


def _normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip()


def _extraer_identificadores(texto: str) -> list[str]:
    identificadores: list[str] = []
    for patron in (_PATRON_NUM_ARTICULO, _PATRON_NUM_DECRETO, _PATRON_NUMERO_CON_UNIDAD):
        identificadores.extend(m.group(1) for m in patron.finditer(texto))
    identificadores.extend(m.group(0) for m in _PATRON_ACRONIMO.finditer(texto))
    return [_normalizar(ident) for ident in identificadores]


def _aparece_en_referencia(identificador: str, referencia_normalizada: str) -> bool:
    """Coincidencia por límites de palabra, no substring ingenuo -- evita que un
    identificador corto (ej. "25") "aparezca" por accidente dentro de un número
    más largo no relacionado (ej. "1250") en la referencia."""
    patron = r"(?<!\w)" + re.escape(identificador) + r"(?!\w)"
    return re.search(patron, referencia_normalizada) is not None


def citas_y_numeros_son_fieles(narrativa: str, brecha_determinista: dict) -> bool:
    """True si todo artículo/decreto, acrónimo de ley y cantidad de tiempo
    mencionados en `narrativa` aparecen también en los campos estructurados de
    `brecha_determinista` (ver `_CAMPOS_REFERENCIA`). False si la narrativa
    introduce al menos uno que no está ahí -- fail-closed, igual que el resto de
    F9: ante duda (identificador no encontrado) se rechaza, nunca se aprueba por
    omisión."""
    referencia = _normalizar(
        " ".join(str(brecha_determinista.get(campo, "")) for campo in _CAMPOS_REFERENCIA)
    )
    return all(
        _aparece_en_referencia(identificador, referencia)
        for identificador in _extraer_identificadores(narrativa)
    )

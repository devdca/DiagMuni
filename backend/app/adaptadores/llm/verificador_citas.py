"""Compuerta determinista de F9 -- sin LLM, sin costo. Corre siempre, antes que
`verificador.py`: si rechaza aquí, no importa qué diría un LLM.

Motivación (docs/plan-implementacion-e1-bis-capa-ia-local.md sección 9): un modelo
local chico (phi3) aprobó de forma reproducible una narrativa con normativa
inventada -- juzgar fidelidad factual con un LLM así de chico no es confiable.

Detecta: artículos/decretos, acrónimos de ley y cantidades de tiempo inventados.
No detecta (limitación real): tergiversar el contenido de una cita que sí existe,
o una contradicción sin número/nombre nuevo -- ver `verificador.py` para la capa
LLM opcional que cubre esos casos, sin garantía."""

import re
import unicodedata

_CAMPOS_REFERENCIA = (
    "paso_administrativo",
    "paso_tecnico",
    "paso_organizacional",
    "por_que_importa",
    "fuente_normativa",
)

# Solo el identificador (dígitos + sufijo "-III"/"bis"), no la palabra "artículo"
# que lo precede -- robusto a reformular "art. 25-III" como "artículo 25, fracción III".
_PATRON_NUM_ARTICULO = re.compile(r"art(?:[íi]culo)?s?\.?\s*(\d+[a-z]*(?:[\-/]\w+)?)", re.IGNORECASE)
_PATRON_NUM_DECRETO = re.compile(
    r"decreto\s*(?:n[uú]m(?:ero)?\.?)?\s*(\d+[a-z]*(?:[\-/]\w+)?)", re.IGNORECASE
)
# Un número sin unidad (ej. "índice 2 a 3") no cuenta -- no es una afirmación
# normativa verificable, generaría demasiados falsos rechazos.
_PATRON_NUMERO_CON_UNIDAD = re.compile(r"(\d+\s*(?:d[ií]as?|mes(?:es)?|a[ñn]os?|horas?))", re.IGNORECASE)
_PATRON_ACRONIMO = re.compile(r"\b[A-ZÑ]{3,}\b")  # LNETB, LFEA, SAT... acrónimo inventado o equivocado


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
    """Por límites de palabra, no substring -- evita que "25" aparezca dentro de "1250"."""
    patron = r"(?<!\w)" + re.escape(identificador) + r"(?!\w)"
    return re.search(patron, referencia_normalizada) is not None


def citas_y_numeros_son_fieles(narrativa: str, brecha_determinista: dict, contexto_gobierno: str = "") -> bool:
    """True si todo artículo/decreto/acrónimo/plazo en `narrativa` aparece en
    `brecha_determinista` o en `contexto_gobierno` (mismo texto que ya vio el
    prompt de redacción). Fail-closed: ante duda se rechaza."""
    referencia = _normalizar(
        " ".join(str(brecha_determinista.get(campo, "")) for campo in _CAMPOS_REFERENCIA) + " " + contexto_gobierno
    )
    return all(
        _aparece_en_referencia(identificador, referencia)
        for identificador in _extraer_identificadores(narrativa)
    )

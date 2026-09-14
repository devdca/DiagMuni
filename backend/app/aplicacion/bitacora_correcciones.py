"""Bitácora de correcciones humanas sobre salidas de la capa de IA -- capa de
aplicación, sin conocer HTTP (mismo criterio que sincronizacion_inegi.py y
preferencia_modelo_ia.py). Ver docstring de la migración 0020 para el diseño
completo (por qué existe, para qué se va a usar, por qué nunca implica
reentrenar nada).

Estado: captura (registrar + listar) cubre `mecanismo_identidad` (Diagnostico.tsx,
CardMecanismoIdentidad) y `consistencia_booleana` (mismo archivo, CardBooleana) --
ambas registran solo cuando el funcionario DESCARTA la sugerencia del
clasificador (la confirmación no es información nueva, nada que corregir).
`correcciones_similares` es el consumidor de few-shot real: dado un texto
nuevo a clasificar, trae las correcciones más parecidas ya confirmadas por un
humano para esa misma `pieza`, para que el prompt las use como ejemplo -- ver
`app/adaptadores/llm/asistente_captura.py`. El otro consumidor descrito en la
migración 0020 (conjunto de evaluación al cambiar de modelo/prompt) sigue sin
construirse -- esta tabla ya alcanza el volumen para servir de few-shot, pero
todavía no para congelar un conjunto de evaluación con significancia real.

TODO (bloqueado, no por decisión de diseño sino por falta del dato): los
endpoints de clasificación (app/adaptadores/http/asistente_captura.py) no
devuelven todavía qué ruta_llm resolvió la llamada -- por eso `ruta_llm` se
guarda como `None` desde el primer integrador (F1 mecanismo_identidad).
Devolver esa información requeriría cambiar la firma de
`clasificar_mecanismo_identidad`/`clasificar_consistencia_booleana`
(app/adaptadores/llm/asistente_captura.py), fuera de alcance de esta pasada."""

from difflib import SequenceMatcher
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CorreccionIa


def registrar_correccion(
    db: Session,
    *,
    tenant_id: UUID,
    creado_por: UUID,
    pieza: str,
    entrada_llm: str,
    salida_llm: str,
    correccion: str,
    tramite_id: UUID | None = None,
    ruta_llm: str | None = None,
) -> CorreccionIa:
    """No hace `commit()` -- quien llama decide cuándo confirmar (mismo criterio
    que `crear_gobierno`). Append-only: no existe una función "actualizar" ni
    "borrar" a propósito, ver docstring de la migración 0020."""
    fila = CorreccionIa(
        tenant_id=tenant_id,
        tramite_id=tramite_id,
        pieza=pieza,
        entrada_llm=entrada_llm,
        salida_llm=salida_llm,
        correccion=correccion,
        ruta_llm=ruta_llm,
        creado_por=creado_por,
    )
    db.add(fila)
    return fila


def listar_correcciones(db: Session, *, pieza: str | None = None, limite: int = 200) -> list[CorreccionIa]:
    """Más reciente primero -- uso previsto: panel de revisión (admin) y como
    fuente de candidatas de `correcciones_similares` de abajo."""
    consulta = select(CorreccionIa).order_by(CorreccionIa.creado_en.desc()).limit(limite)
    if pieza is not None:
        consulta = consulta.where(CorreccionIa.pieza == pieza)
    return list(db.execute(consulta).scalars().all())


# Candidatas a considerar antes de rankear por similitud -- suficiente para que
# el ejemplo más parecido real esté casi siempre entre las últimas 50
# correcciones de una `pieza`, sin traer la tabla entera a Python cada vez que
# se clasifica algo (la tabla es append-only, va a seguir creciendo).
_CANDIDATAS_PARA_SIMILITUD = 50


def correcciones_similares(
    db: Session, *, pieza: str, entrada_llm: str, limite: int = 3
) -> list[CorreccionIa]:
    """El consumidor de few-shot real (ver docstring del módulo): las `limite`
    correcciones ya confirmadas por un humano más parecidas a `entrada_llm`
    para esta `pieza`, del tenant de la sesión (aislado por RLS, igual que
    `listar_correcciones`). Similitud de texto simple -- `difflib.SequenceMatcher`
    sobre `entrada_llm`, sin dependencia nueva ni vector store: con el volumen
    de correcciones humanas esperado (no eventos automáticos, cada fila es una
    corrección real de un funcionario) esto alcanza; una búsqueda semántica de
    verdad es una mejora futura si el volumen lo justifica, no un requisito de
    esta primera pasada. Lista vacía si todavía no hay ninguna corrección
    confirmada para esta `pieza` -- el llamador debe tratarlo como "sin
    ejemplos", nunca como error."""
    candidatas = listar_correcciones(db, pieza=pieza, limite=_CANDIDATAS_PARA_SIMILITUD)
    con_similitud = [(SequenceMatcher(None, entrada_llm, c.entrada_llm).ratio(), c) for c in candidatas]
    con_similitud.sort(key=lambda par: par[0], reverse=True)
    return [correccion for _, correccion in con_similitud[:limite]]

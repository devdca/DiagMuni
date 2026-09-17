"""Bitácora de correcciones humanas sobre salidas de la capa de IA. Captura
solo cuando el funcionario DESCARTA la sugerencia del clasificador (confirmar
no es información nueva). `correcciones_similares` alimenta el few-shot real
del prompt de clasificación -- el consumidor de "conjunto de evaluación" al
cambiar de modelo/prompt todavía no se construye (falta volumen)."""

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
    """No hace `commit()`. Append-only a propósito: no hay "actualizar" ni "borrar"."""
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


# Suficiente para que el ejemplo más parecido esté casi siempre en las últimas
# 50 correcciones, sin traer la tabla entera a Python en cada clasificación.
_CANDIDATAS_PARA_SIMILITUD = 50


def correcciones_similares(
    db: Session, *, pieza: str, entrada_llm: str, limite: int = 3
) -> list[CorreccionIa]:
    """Las `limite` correcciones más parecidas a `entrada_llm` para esta `pieza`
    (few-shot del prompt). Similitud simple (`difflib.SequenceMatcher`), sin
    vector store -- alcanza para el volumen esperado. Lista vacía si no hay
    ninguna corrección confirmada todavía, no es un error."""
    candidatas = listar_correcciones(db, pieza=pieza, limite=_CANDIDATAS_PARA_SIMILITUD)
    con_similitud = [(SequenceMatcher(None, entrada_llm, c.entrada_llm).ratio(), c) for c in candidatas]
    con_similitud.sort(key=lambda par: par[0], reverse=True)
    return [correccion for _, correccion in con_similitud[:limite]]

"""Snapshot del índice de madurez global del tenant (migración 0015) -- un
punto cada vez que `enviar_diagnostico` (app/adaptadores/http/diagnosticos.py)
recalcula el índice de un trámite. Alimenta la gráfica real de tendencia del
Panel de control -- nunca datos simulados. Migración 0016 sumó el conteo de
trámites en cada nivel (0-4) al mismo snapshot, para la gráfica apilada por
nivel (pedido explícito: que se vea como un "gradient stacked area chart",
pero con datos reales -- cuántos trámites hay en cada nivel de la rampa, no
series inventadas)."""

from collections import Counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dominio.madurez import calcular_indice_global
from app.models import DiagnosticoTramite, HistorialIndiceGlobal, Tramite


def registrar_snapshot_indice_global(db: Session, *, tenant_id: UUID) -> HistorialIndiceGlobal | None:
    """Recalcula el índice global con los MISMOS trámites y la MISMA fórmula que
    el panel resumen (app/adaptadores/http/tramites.py::listar_tramites --
    solo trámites activos, `calcular_indice_global`) y guarda un punto nuevo,
    junto con cuántos de esos trámites están en cada nivel (0-4) -- ambos
    números salen del mismo `indices`, en el mismo instante.

    No hace `commit()` -- se llama desde dentro de la transacción de
    enviar_diagnostico, mismo criterio que `app.aplicacion.historial.registrar_evento`:
    un punto nunca queda persistido sin que el envío que lo originó también lo
    esté, ni viceversa.

    Devuelve `None` (no guarda nada) si el tenant todavía no tiene ningún
    trámite diagnosticado -- un punto sin valor no aporta a una tendencia."""
    tramites_activos = list(db.execute(select(Tramite.id).where(Tramite.archivado_en.is_(None))).scalars())
    if not tramites_activos:
        return None

    indices = list(
        db.execute(
            select(DiagnosticoTramite.indice_madurez).where(DiagnosticoTramite.tramite_id.in_(tramites_activos))
        ).scalars()
    )
    indice_global = calcular_indice_global(indices)
    if indice_global is None:
        return None

    # Solo cuenta trámites YA diagnosticados (indice_madurez no nulo) -- mismo
    # criterio que calcular_indice_global, nunca se le asume un nivel a uno
    # sin diagnosticar.
    conteo_por_nivel = Counter(nivel for nivel in indices if nivel is not None)

    snapshot = HistorialIndiceGlobal(
        tenant_id=tenant_id,
        indice_global=indice_global,
        nivel_0_conteo=conteo_por_nivel.get(0, 0),
        nivel_1_conteo=conteo_por_nivel.get(1, 0),
        nivel_2_conteo=conteo_por_nivel.get(2, 0),
        nivel_3_conteo=conteo_por_nivel.get(3, 0),
        nivel_4_conteo=conteo_por_nivel.get(4, 0),
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def listar_historial_indice_global(db: Session, *, tenant_id: UUID) -> list[HistorialIndiceGlobal]:
    """Más antiguo primero -- es el orden que una gráfica de tendencia
    necesita para dibujarse de izquierda a derecha, al revés de
    `listar_historial` (línea de tiempo de trámite, más reciente primero)."""
    return list(
        db.execute(
            select(HistorialIndiceGlobal)
            .where(HistorialIndiceGlobal.tenant_id == tenant_id)
            .order_by(HistorialIndiceGlobal.creado_en.asc())
        ).scalars()
    )

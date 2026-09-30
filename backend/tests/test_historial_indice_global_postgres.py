"""Tests de `app/aplicacion/historial_indice_global.py` contra Postgres real --
snapshot del índice global (migración 0015) que alimenta la gráfica de
tendencia real del panel resumen."""

import socket
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.aplicacion.historial_indice_global import listar_historial_indice_global, registrar_snapshot_indice_global
from app.core.config import settings
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.models import DiagnosticoTramite, Tenant, Tramite


def _postgres_real_disponible() -> bool:
    url = urlparse(settings.database_url.replace("postgresql+psycopg", "postgresql", 1))
    try:
        with socket.create_connection((url.hostname or "localhost", url.port or 5432), timeout=2):
            pass
    except OSError:
        return False
    try:
        db = abrir_sesion_tenant(uuid4())
    except Exception:
        return False
    db.close()
    return True


pytestmark = pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)


@pytest.fixture
def tenant_vacio():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant historial índice", clave=f"prueba-hig-{tenant_id}", pais="mx"))
        db.commit()
    finally:
        db.close()

    yield tenant_id

    db = abrir_sesion_tenant(tenant_id)
    try:
        # Orden por FK: diagnostico_tramite/historial_indice_global antes que
        # tramite/tenant -- a diferencia de evento_historial (ondelete=CASCADE),
        # ninguna de las dos tiene borrado en cascada declarado.
        db.execute(text("DELETE FROM diagnostico_tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM historial_indice_global WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
        db.commit()
    finally:
        db.close()


def _crear_tramite_diagnosticado(db, tenant_id, indice: int) -> None:
    tramite = Tramite(tenant_id=tenant_id, nombre=f"Trámite índice {indice}")
    db.add(tramite)
    db.flush()
    db.add(DiagnosticoTramite(tramite_id=tramite.id, tenant_id=tenant_id, respuestas={}, indice_madurez=indice))
    db.flush()


def test_sin_ningun_tramite_no_guarda_nada(tenant_vacio):
    db = abrir_sesion_tenant(tenant_vacio)
    try:
        assert registrar_snapshot_indice_global(db, tenant_id=tenant_vacio) is None
        db.commit()
        fijar_contexto_tenant(db, tenant_vacio)
        assert listar_historial_indice_global(db, tenant_id=tenant_vacio) == []
    finally:
        db.close()


def test_sin_ningun_diagnostico_completo_no_guarda_nada(tenant_vacio):
    """Trámite catalogado pero sin diagnóstico enviado -- distinto del caso de
    arriba (0 trámites): acá sí hay un trámite, pero `indice_madurez` sigue en
    None, así que tampoco hay nada real que graficar todavía."""
    db = abrir_sesion_tenant(tenant_vacio)
    try:
        tramite = Tramite(tenant_id=tenant_vacio, nombre="Sin diagnosticar")
        db.add(tramite)
        db.flush()

        assert registrar_snapshot_indice_global(db, tenant_id=tenant_vacio) is None
        db.commit()
    finally:
        db.close()


def test_registra_snapshot_con_el_promedio_correcto(tenant_vacio):
    db = abrir_sesion_tenant(tenant_vacio)
    try:
        _crear_tramite_diagnosticado(db, tenant_vacio, indice=4)
        _crear_tramite_diagnosticado(db, tenant_vacio, indice=0)

        snapshot = registrar_snapshot_indice_global(db, tenant_id=tenant_vacio)
        db.commit()

        assert snapshot is not None
        assert snapshot.indice_global == 2.0  # promedio de 4 y 0, misma fórmula que el panel resumen
    finally:
        db.close()


def test_tramite_archivado_no_cuenta_en_el_snapshot(tenant_vacio):
    """Mismo criterio que el panel resumen (app/adaptadores/http/tramites.py::
    listar_tramites): un trámite archivado nunca infla ni corrompe el índice
    global -- ni en la lectura instantánea ni en el historial persistido."""
    db = abrir_sesion_tenant(tenant_vacio)
    try:
        _crear_tramite_diagnosticado(db, tenant_vacio, indice=4)

        tramite_archivado = Tramite(tenant_id=tenant_vacio, nombre="Archivado", archivado_en=datetime.now(UTC))
        db.add(tramite_archivado)
        db.flush()
        db.add(
            DiagnosticoTramite(
                tramite_id=tramite_archivado.id, tenant_id=tenant_vacio, respuestas={}, indice_madurez=0
            )
        )
        db.flush()

        snapshot = registrar_snapshot_indice_global(db, tenant_id=tenant_vacio)
        db.commit()

        assert snapshot is not None
        assert snapshot.indice_global == 4.0  # el archivado (índice 0) queda fuera del promedio
    finally:
        db.close()


def test_listar_historial_indice_global_mas_antiguo_primero(tenant_vacio):
    """Orden inverso al de `listar_historial` (línea de tiempo de un trámite) --
    una gráfica de tendencia se dibuja de izquierda a derecha."""
    db = abrir_sesion_tenant(tenant_vacio)
    try:
        _crear_tramite_diagnosticado(db, tenant_vacio, indice=1)
        registrar_snapshot_indice_global(db, tenant_id=tenant_vacio)
        db.commit()

        fijar_contexto_tenant(db, tenant_vacio)
        _crear_tramite_diagnosticado(db, tenant_vacio, indice=3)
        registrar_snapshot_indice_global(db, tenant_id=tenant_vacio)
        db.commit()

        fijar_contexto_tenant(db, tenant_vacio)
        puntos = listar_historial_indice_global(db, tenant_id=tenant_vacio)
        assert [p.indice_global for p in puntos] == [1.0, 2.0]  # 1º: solo el trámite de índice 1; 2º: promedio (1+3)/2
    finally:
        db.close()

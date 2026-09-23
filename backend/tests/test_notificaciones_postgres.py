"""Tests de `app/aplicacion/notificaciones.py` contra Postgres real (migración
0013, centro de notificaciones)."""

import socket
from datetime import date, timedelta
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.aplicacion.notificaciones import (
    TIPO_ACCION_ATRASADA,
    contar_no_leidas,
    crear_notificacion,
    generar_notificaciones_acciones_atrasadas,
    listar_notificaciones,
    marcar_leida,
    marcar_todas_leidas,
)
from app.core.config import settings
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.models import AccionSeguimiento, DiagnosticoTramite, PlanModernizacion, Tenant, Tramite


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
def tenant_simple():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant notificaciones", clave=f"prueba-notif-{tenant_id}", pais="mx"))
        db.commit()
    finally:
        db.close()

    yield tenant_id

    db = abrir_sesion_tenant(tenant_id)
    try:
        # Orden por dependencias: notificacion/accion_seguimiento antes que
        # plan_modernizacion/diagnostico_tramite, y esos antes que tramite -- ninguna
        # de esas FK tiene ondelete=CASCADE hacia tramite (solo evento_historial y
        # notificacion lo tienen, y solo para su propio tramite_id/accion_seguimiento_id).
        db.execute(text("DELETE FROM notificacion WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(
            text(
                "DELETE FROM accion_seguimiento WHERE plan_modernizacion_id IN "
                "(SELECT id FROM plan_modernizacion WHERE tenant_id = :t)"
            ),
            {"t": str(tenant_id)},
        )
        db.execute(text("DELETE FROM plan_modernizacion WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM diagnostico_tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
        db.commit()
    finally:
        db.close()


def test_crear_listar_marcar_leida(tenant_simple):
    tenant_id = tenant_simple
    db = abrir_sesion_tenant(tenant_id)
    try:
        n = crear_notificacion(db, tenant_id=tenant_id, tipo="x", titulo="Título", mensaje="Mensaje")
        db.commit()
        fijar_contexto_tenant(db, tenant_id)

        assert contar_no_leidas(db, tenant_id=tenant_id) == 1
        assert len(listar_notificaciones(db, tenant_id=tenant_id)) == 1

        actualizada = marcar_leida(db, tenant_id=tenant_id, notificacion_id=n.id)
        db.commit()
        assert actualizada.leida is True

        fijar_contexto_tenant(db, tenant_id)
        assert contar_no_leidas(db, tenant_id=tenant_id) == 0
    finally:
        db.close()


def test_marcar_todas_leidas(tenant_simple):
    tenant_id = tenant_simple
    db = abrir_sesion_tenant(tenant_id)
    try:
        crear_notificacion(db, tenant_id=tenant_id, tipo="a", titulo="A", mensaje="a")
        crear_notificacion(db, tenant_id=tenant_id, tipo="b", titulo="B", mensaje="b")
        db.commit()
        fijar_contexto_tenant(db, tenant_id)

        marcar_todas_leidas(db, tenant_id=tenant_id)
        db.commit()

        fijar_contexto_tenant(db, tenant_id)
        assert contar_no_leidas(db, tenant_id=tenant_id) == 0
    finally:
        db.close()


@pytest.fixture
def tenant_con_accion_atrasada(tenant_simple):
    tenant_id = tenant_simple
    db = abrir_sesion_tenant(tenant_id)
    try:
        tramite = Tramite(tenant_id=tenant_id, nombre="Trámite atrasado", estado="plan_listo")
        db.add(tramite)
        db.flush()
        diagnostico = DiagnosticoTramite(tenant_id=tenant_id, tramite_id=tramite.id, respuestas={})
        db.add(diagnostico)
        db.flush()
        plan = PlanModernizacion(
            diagnostico_tramite_id=diagnostico.id,
            tenant_id=tenant_id,
            version=1,
            modo="degradado",
            contenido={"resumen_narrativo": "x", "brechas": []},
            verificado=True,
        )
        db.add(plan)
        db.flush()
        accion = AccionSeguimiento(
            plan_modernizacion_id=plan.id,
            tenant_id=tenant_id,
            descripcion="Acción vencida",
            responsable="Por asignar",
            fecha_objetivo=date.today() - timedelta(days=3),
        )
        db.add(accion)
        db.commit()
        accion_id = accion.id
    finally:
        db.close()

    return tenant_id, accion_id


def test_generar_notificaciones_acciones_atrasadas_crea_una_por_accion(tenant_con_accion_atrasada):
    tenant_id, accion_id = tenant_con_accion_atrasada
    db = abrir_sesion_tenant(tenant_id)
    try:
        generar_notificaciones_acciones_atrasadas(db, tenant_id=tenant_id)
        db.commit()

        fijar_contexto_tenant(db, tenant_id)
        notificaciones = listar_notificaciones(db, tenant_id=tenant_id)
        atrasadas = [n for n in notificaciones if n.tipo == TIPO_ACCION_ATRASADA]
        assert len(atrasadas) == 1
        assert atrasadas[0].accion_seguimiento_id == accion_id
    finally:
        db.close()


def test_generar_notificaciones_acciones_atrasadas_no_duplica_en_segunda_corrida(tenant_con_accion_atrasada):
    tenant_id, _accion_id = tenant_con_accion_atrasada
    db = abrir_sesion_tenant(tenant_id)
    try:
        generar_notificaciones_acciones_atrasadas(db, tenant_id=tenant_id)
        db.commit()
        fijar_contexto_tenant(db, tenant_id)

        generar_notificaciones_acciones_atrasadas(db, tenant_id=tenant_id)
        db.commit()

        fijar_contexto_tenant(db, tenant_id)
        atrasadas = [n for n in listar_notificaciones(db, tenant_id=tenant_id) if n.tipo == TIPO_ACCION_ATRASADA]
        assert len(atrasadas) == 1
    finally:
        db.close()

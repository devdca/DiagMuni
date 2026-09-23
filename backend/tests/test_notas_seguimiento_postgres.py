"""Tests de `app/aplicacion/notas_seguimiento.py` contra Postgres real (migración
0014, notas colaborativas de seguimiento)."""

import socket
from datetime import date
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.aplicacion.gestion_usuarios import _crear_fila_usuario
from app.aplicacion.notas_seguimiento import crear_nota, listar_notas
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
def escenario_completo():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant notas", clave=f"prueba-notas-{tenant_id}", pais="mx"))
        db.flush()
        usuario, _password = _crear_fila_usuario(
            db, tenant_id=tenant_id, email="autor@prueba-notas.mx", nombre="Autor de Prueba", rol="funcionario"
        )
        tramite = Tramite(tenant_id=tenant_id, nombre="Trámite con notas", estado="plan_listo")
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
            descripcion="Acción con notas",
            responsable="Por asignar",
            fecha_objetivo=date.today(),
        )
        db.add(accion)
        db.commit()
        accion_id, usuario_id = accion.id, usuario.id
    finally:
        db.close()

    yield tenant_id, accion_id, usuario_id

    db = abrir_sesion_tenant(tenant_id)
    try:
        db.execute(text("DELETE FROM nota_seguimiento WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM accion_seguimiento WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM plan_modernizacion WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM diagnostico_tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM usuario WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
        db.commit()
    finally:
        db.close()


def test_crear_y_listar_notas_en_orden_cronologico(escenario_completo):
    tenant_id, accion_id, usuario_id = escenario_completo
    db = abrir_sesion_tenant(tenant_id)
    try:
        crear_nota(
            db, tenant_id=tenant_id, accion_seguimiento_id=accion_id, usuario_id=usuario_id, texto="Primera nota"
        )
        db.commit()
        fijar_contexto_tenant(db, tenant_id)
        crear_nota(
            db, tenant_id=tenant_id, accion_seguimiento_id=accion_id, usuario_id=usuario_id, texto="Segunda nota"
        )
        db.commit()

        fijar_contexto_tenant(db, tenant_id)
        notas = listar_notas(db, tenant_id=tenant_id, accion_seguimiento_id=accion_id)
        assert [nota.texto for nota, _autor in notas] == ["Primera nota", "Segunda nota"]
        assert all(autor == "Autor de Prueba" for _nota, autor in notas)
    finally:
        db.close()


def test_nota_recorta_espacios_en_blanco(escenario_completo):
    tenant_id, accion_id, usuario_id = escenario_completo
    db = abrir_sesion_tenant(tenant_id)
    try:
        nota = crear_nota(
            db, tenant_id=tenant_id, accion_seguimiento_id=accion_id, usuario_id=usuario_id, texto="  con espacios  "
        )
        assert nota.texto == "con espacios"
    finally:
        db.rollback()
        db.close()

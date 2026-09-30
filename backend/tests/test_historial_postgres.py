"""Tests de `app/aplicacion/historial.py` contra Postgres real -- bitácora
persistida por trámite (migración 0012, pantalla "Historial")."""

import socket
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.aplicacion.historial import TIPO_DIAGNOSTICO_ENVIADO, listar_historial, registrar_evento
from app.core.config import settings
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.models import Tenant, Tramite


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
def tenant_con_tramite():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant historial", clave=f"prueba-historial-{tenant_id}", pais="mx"))
        db.flush()
        tramite = Tramite(tenant_id=tenant_id, nombre="Trámite de prueba historial")
        db.add(tramite)
        db.commit()
        tramite_id = tramite.id
    finally:
        db.close()

    yield tenant_id, tramite_id

    db = abrir_sesion_tenant(tenant_id)
    try:
        db.execute(text("DELETE FROM tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
        db.commit()
    finally:
        db.close()


def test_registrar_y_listar_evento(tenant_con_tramite):
    tenant_id, tramite_id = tenant_con_tramite
    db = abrir_sesion_tenant(tenant_id)
    try:
        registrar_evento(
            db,
            tenant_id=tenant_id,
            tramite_id=tramite_id,
            tipo=TIPO_DIAGNOSTICO_ENVIADO,
            descripcion="Diagnóstico enviado -- índice de madurez calculado: 2.",
            metadatos={"indice_madurez": 2},
        )
        db.commit()

        fijar_contexto_tenant(db, tenant_id)
        eventos = listar_historial(db, tenant_id=tenant_id, tramite_id=tramite_id)
        assert len(eventos) == 1
        assert eventos[0].tipo == TIPO_DIAGNOSTICO_ENVIADO
        assert eventos[0].metadatos == {"indice_madurez": 2}
    finally:
        db.close()


def test_listar_historial_mas_reciente_primero(tenant_con_tramite):
    tenant_id, tramite_id = tenant_con_tramite
    db = abrir_sesion_tenant(tenant_id)
    try:
        registrar_evento(db, tenant_id=tenant_id, tramite_id=tramite_id, tipo="uno", descripcion="Primero")
        db.commit()
        fijar_contexto_tenant(db, tenant_id)
        registrar_evento(db, tenant_id=tenant_id, tramite_id=tramite_id, tipo="dos", descripcion="Segundo")
        db.commit()

        fijar_contexto_tenant(db, tenant_id)
        eventos = listar_historial(db, tenant_id=tenant_id, tramite_id=tramite_id)
        assert [e.tipo for e in eventos] == ["dos", "uno"]
    finally:
        db.close()


def test_eliminar_tramite_borra_en_cascada_sus_eventos_de_historial(tenant_con_tramite):
    """Regresión: `eliminar_tramite` (app/adaptadores/http/tramites.py) permite
    borrado físico de un trámite archivado sin diagnóstico enviado -- si ya tiene
    eventos de historial, el DELETE de `tramite` no debe reventar por la FK
    (ondelete=CASCADE, migración 0012)."""
    tenant_id, tramite_id = tenant_con_tramite
    db = abrir_sesion_tenant(tenant_id)
    try:
        registrar_evento(db, tenant_id=tenant_id, tramite_id=tramite_id, tipo="tramite_archivado", descripcion="x")
        db.commit()

        fijar_contexto_tenant(db, tenant_id)
        db.execute(text("DELETE FROM tramite WHERE id = :id"), {"id": str(tramite_id)})
        db.commit()  # no debe lanzar ForeignKeyViolation

        fijar_contexto_tenant(db, tenant_id)
        restantes = db.execute(
            text("SELECT count(*) FROM evento_historial WHERE tramite_id = :id"), {"id": str(tramite_id)}
        ).scalar_one()
        assert restantes == 0
    finally:
        db.close()

"""Tests de `POST /api/tramites/{id}/diagnostico/simular` -- cálculo del motor
determinista sobre respuestas hipotéticas, sin persistir nada."""

import socket
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.adaptadores.http.deps import TokenData
from app.adaptadores.http.diagnosticos import simular_diagnostico
from app.core.config import settings
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.models import DiagnosticoTramite, Tenant, Tramite
from app.schemas.diagnostico import DiagnosticoGuardar


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
        db.add(Tenant(id=tenant_id, nombre="Tenant simulador", clave=f"prueba-simulador-{tenant_id}", pais="mx"))
        db.flush()
        tramite = Tramite(tenant_id=tenant_id, nombre="Trámite simulador")
        db.add(tramite)
        db.commit()
        tramite_id = tramite.id
    finally:
        db.close()

    yield tenant_id, tramite_id

    db = abrir_sesion_tenant(tenant_id)
    try:
        db.execute(text("DELETE FROM diagnostico_tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
        db.commit()
    finally:
        db.close()


def test_simular_sin_diagnostico_previo_indice_actual_es_none(tenant_con_tramite):
    tenant_id, tramite_id = tenant_con_tramite
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        payload = DiagnosticoGuardar(respuestas={})

        resultado = simular_diagnostico(tramite_id, payload, token, db)

        assert resultado.indice_actual is None
        assert resultado.indice_proyectado == 0  # sin nada respondido, todo cuenta como false -> nivel 0
    finally:
        db.close()


def test_simular_proyecta_nivel_4_con_todas_las_variables_en_true(tenant_con_tramite):
    tenant_id, tramite_id = tenant_con_tramite
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        payload = DiagnosticoGuardar(
            respuestas={
                "documentos_digitalizados": True,
                "motor_pagos": True,
                "firma_electronica_habilitada": True,
                "interoperabilidad": True,
                "mecanismo_identidad": "propio",
            }
        )

        resultado = simular_diagnostico(tramite_id, payload, token, db)

        assert resultado.indice_proyectado == 4
    finally:
        db.close()


def test_simular_no_persiste_nada(tenant_con_tramite):
    """El diagnóstico sigue sin existir después de simular -- a diferencia de
    `guardar_diagnostico`/`enviar_diagnostico`."""
    tenant_id, tramite_id = tenant_con_tramite
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        payload = DiagnosticoGuardar(respuestas={"documentos_digitalizados": True})

        simular_diagnostico(tramite_id, payload, token, db)

        fijar_contexto_tenant(db, tenant_id)
        total = db.execute(
            text("SELECT count(*) FROM diagnostico_tramite WHERE tramite_id = :t"), {"t": str(tramite_id)}
        ).scalar_one()
        assert total == 0
    finally:
        db.close()


def test_simular_refleja_indice_actual_de_un_diagnostico_ya_enviado(tenant_con_tramite):
    tenant_id, tramite_id = tenant_con_tramite
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(DiagnosticoTramite(tenant_id=tenant_id, tramite_id=tramite_id, respuestas={}, indice_madurez=2))
        db.commit()
        fijar_contexto_tenant(db, tenant_id)

        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        payload = DiagnosticoGuardar(respuestas={})
        resultado = simular_diagnostico(tramite_id, payload, token, db)

        assert resultado.indice_actual == 2
    finally:
        db.close()

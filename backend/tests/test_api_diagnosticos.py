"""Test de `guardar_diagnostico` (backend/app/api/diagnosticos.py) contra Postgres
real -- mismo criterio ya documentado en test_api_seguimiento.py: la función hace
`db.get(Tramite, ...)`, un `select` vía `_obtener_o_crear_diagnostico` y un
`db.commit()`, así que no es una función pura testeable sin sesión real. Se salta
limpio (no falla) si no hay Postgres alcanzable con el `DATABASE_URL` configurado
(CI no lo provisiona para esta suite, ver .github/workflows/ci.yml), pero corriendo
contra `docker compose up db` ejercita la transición de estado de verdad.

Cubre el caso de docs/app-flow.md (líneas 47 y 61): un trámite en `plan_listo` que
se reabre y guarda vía "Guardar y continuar después" debe volver a `en_progreso`,
no quedarse en `plan_listo`.
"""

import json
import logging
import socket
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import select, text

from app.api.deps import TokenData
from app.api.diagnosticos import enviar_diagnostico, guardar_diagnostico
from app.core.config import settings
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.models import Job, Tenant, Tramite
from app.schemas.diagnostico import DiagnosticoEnviar, DiagnosticoGuardar


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


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_guardar_diagnostico_regresa_a_en_progreso_desde_plan_listo_contra_postgres_real():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant de prueba diagnostico", clave=f"prueba-diag-{tenant_id}", pais="mx"))
        db.flush()

        tramite = Tramite(tenant_id=tenant_id, nombre="Trámite de prueba diagnostico", estado="plan_listo")
        db.add(tramite)
        db.commit()
        # el commit anterior resetea el contexto de tenant local (mismo motivo
        # documentado en test_api_seguimiento.py) -- hay que refijarlo antes de
        # que `guardar_diagnostico` haga su primer `db.get`.
        fijar_contexto_tenant(db, tenant_id)

        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        payload = DiagnosticoGuardar(respuestas={"algo": "editado"})

        resultado = guardar_diagnostico(tramite.id, payload, token, db)

        fijar_contexto_tenant(db, tenant_id)
        db.refresh(tramite)
        assert tramite.estado == "en_progreso"
        assert resultado.respuestas == {"algo": "editado"}
    finally:
        try:
            db.execute(text("DELETE FROM diagnostico_tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
            db.execute(text("DELETE FROM tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
            db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_enviar_diagnostico_no_revienta_rls_tras_commit_contra_postgres_real(caplog):
    """Regresión: `enviar_diagnostico` hacía `db.commit()` sin volver a fijar el
    contexto de tenant -- una consulta real posterior en la misma sesión (acá, el
    `select` sobre `job`) revienta con `invalid input syntax for type uuid: ""`,
    mismo patrón ya corregido antes en `plan_job.py` y `seguimiento.py`.

    También cubre el log de auditoría (app/core/audit_log.py, Fase G2) en el
    punto de llamada real -- test_audit_log.py ya prueba la función aislada, esto
    confirma que `enviar_diagnostico` de verdad la invoca con datos reales."""
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant de prueba diagnostico", clave=f"prueba-diag-{tenant_id}", pais="mx"))
        db.flush()

        tramite = Tramite(tenant_id=tenant_id, nombre="Trámite de prueba diagnostico", estado="diagnosticado")
        db.add(tramite)
        db.commit()
        fijar_contexto_tenant(db, tenant_id)

        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        payload = DiagnosticoEnviar(
            respuestas={
                "documentos_digitalizados": True,
                "motor_pagos": True,
                "firma_electronica_habilitada": True,
                "interoperabilidad": True,
                "mecanismo_identidad": "propio",
            }
        )

        with caplog.at_level(logging.INFO, logger="diagmuni.auditoria"):
            resultado = enviar_diagnostico(tramite.id, payload, token, db, BackgroundTasks())

        assert resultado.indice_madurez is not None

        [registro_auditoria] = [r for r in caplog.records if r.name == "diagmuni.auditoria"]
        linea = json.loads(registro_auditoria.message)
        assert linea["evento"] == "diagnostico_enviado"
        assert linea["tenant_id"] == str(tenant_id)
        assert linea["diagnostico_id"] == str(resultado.id)
        assert linea["indice_madurez"] == resultado.indice_madurez

        # La consulta real que antes revienta: después del `db.commit()` interno de
        # `enviar_diagnostico`, una consulta con RLS en la misma sesión debe seguir
        # funcionando -- acá, releer el job que la propia función creó.
        job = db.execute(select(Job).where(Job.diagnostico_tramite_id == resultado.id)).scalar_one()
        assert job.estado == "pending"

        db.refresh(tramite)
        assert tramite.estado == "generando_plan"
    finally:
        try:
            db.execute(text("DELETE FROM job WHERE tenant_id = :t"), {"t": str(tenant_id)})
            db.execute(text("DELETE FROM diagnostico_tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
            db.execute(text("DELETE FROM tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
            db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

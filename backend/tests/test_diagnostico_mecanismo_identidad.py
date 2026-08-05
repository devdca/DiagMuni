"""Cubre la validación server-side de `mecanismo_identidad` (docs/ux-brief.md línea
71): ese campo, cuando está presente en `respuestas`, solo puede tomar uno de los 4
valores catalogados en el frontend (`ETIQUETA_MECANISMO` en Diagnostico.tsx), nunca
un "otro" sin resolver ni ningún otro texto libre.

La primera tanda de tests ejercita `_validar_mecanismo_identidad` directamente --
es una función pura (dict -> None o HTTPException), no necesita sesión de DB.
La segunda tanda, igual que test_api_diagnosticos.py, ejercita `guardar_diagnostico`
y `enviar_diagnostico` completos contra Postgres real y se salta limpio si no hay
uno alcanzable con el `DATABASE_URL` configurado.
"""

import socket
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import text

from app.api.deps import TokenData
from app.api.diagnosticos import _validar_mecanismo_identidad, enviar_diagnostico, guardar_diagnostico
from app.core.config import settings
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.models import Tenant, Tramite
from app.schemas.diagnostico import DiagnosticoEnviar, DiagnosticoGuardar

VALORES_CANONICOS = ("llave_mx", "id_uruguay", "propio", "ninguno")
VALORES_INVALIDOS = ("otro", "xyz", "")


# --- _validar_mecanismo_identidad (sin DB) -----------------------------------------


def test_mecanismo_identidad_ausente_no_rechaza():
    _validar_mecanismo_identidad({"documentos_digitalizados": True})


@pytest.mark.parametrize("valor", VALORES_CANONICOS)
def test_mecanismo_identidad_valor_canonico_no_rechaza(valor):
    _validar_mecanismo_identidad({"mecanismo_identidad": valor})


@pytest.mark.parametrize("valor", VALORES_INVALIDOS)
def test_mecanismo_identidad_valor_invalido_rechaza_con_422(valor):
    with pytest.raises(HTTPException) as excinfo:
        _validar_mecanismo_identidad({"mecanismo_identidad": valor})
    assert excinfo.value.status_code == 422
    detalle = str(excinfo.value.detail)
    assert valor in detalle or "no es una opción válida" in detalle
    for opcion in VALORES_CANONICOS:
        assert opcion in detalle


# --- integración contra Postgres real ----------------------------------------------


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


REQUIERE_POSTGRES = pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)


def _crear_tenant_y_tramite(db, tenant_id, estado="en_progreso"):
    db.add(Tenant(id=tenant_id, nombre="Tenant de prueba mecanismo", clave=f"prueba-mec-{tenant_id}", pais="mx"))
    db.flush()
    tramite = Tramite(tenant_id=tenant_id, nombre="Trámite de prueba mecanismo", estado=estado)
    db.add(tramite)
    db.commit()
    fijar_contexto_tenant(db, tenant_id)
    return tramite


def _limpiar(db, tenant_id):
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


@REQUIERE_POSTGRES
def test_guardar_diagnostico_rechaza_mecanismo_identidad_invalido_contra_postgres_real():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        tramite = _crear_tenant_y_tramite(db, tenant_id)
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        payload = DiagnosticoGuardar(respuestas={"mecanismo_identidad": "otro"})

        with pytest.raises(HTTPException) as excinfo:
            guardar_diagnostico(tramite.id, payload, token, db)
        assert excinfo.value.status_code == 422
    finally:
        _limpiar(db, tenant_id)


@REQUIERE_POSTGRES
def test_guardar_diagnostico_acepta_mecanismo_identidad_canonico_contra_postgres_real():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        tramite = _crear_tenant_y_tramite(db, tenant_id)
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        payload = DiagnosticoGuardar(respuestas={"mecanismo_identidad": "propio"})

        resultado = guardar_diagnostico(tramite.id, payload, token, db)

        assert resultado.respuestas == {"mecanismo_identidad": "propio"}
    finally:
        _limpiar(db, tenant_id)


@REQUIERE_POSTGRES
def test_enviar_diagnostico_rechaza_mecanismo_identidad_invalido_contra_postgres_real():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        tramite = _crear_tenant_y_tramite(db, tenant_id)
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        payload = DiagnosticoEnviar(
            respuestas={
                "documentos_digitalizados": True,
                "motor_pagos": True,
                "firma_electronica_habilitada": True,
                "interoperabilidad": True,
                "mecanismo_identidad": "xyz",
            }
        )

        with pytest.raises(HTTPException) as excinfo:
            enviar_diagnostico(tramite.id, payload, token, db, BackgroundTasks())
        assert excinfo.value.status_code == 422
    finally:
        _limpiar(db, tenant_id)

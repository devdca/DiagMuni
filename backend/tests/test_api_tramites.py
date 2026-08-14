"""Tests de eliminar/archivar/desarchivar un trámite (backend/app/api/tramites.py)
contra Postgres real -- mismo criterio que test_api_diagnosticos.py: estas
funciones hacen `db.get`/`db.delete`/`db.commit`, no son puras testeables sin
sesión real. Se saltan limpio si no hay Postgres alcanzable.

Cubre el diseño real: DELETE físico solo antes del primer envío de diagnóstico
(guard por dato, no por `estado`); archivado reversible después, sin borrar
ninguna fila; ambos excluidos/incluidos correctamente del panel resumen
(índice global, fecha de último diagnóstico) y de /api/seguimiento.
"""

import json
import logging
import socket
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import text

from app.api.deps import TokenData
from app.api.seguimiento import listar_acciones
from app.api.tramites import archivar_tramite, desarchivar_tramite, eliminar_tramite, listar_tramites
from app.core.config import settings
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.models import (
    AccionSeguimiento,
    DiagnosticoTramite,
    PlanModernizacion,
    Tenant,
    Tramite,
)


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


def _preparar_tenant_y_tramite(db, tenant_id, *, nombre="Trámite de prueba tramites-api", estado="sin_iniciar"):
    db.add(Tenant(id=tenant_id, nombre="Tenant de prueba tramites-api", clave=f"prueba-tram-{tenant_id}", pais="mx"))
    db.flush()
    tramite = Tramite(tenant_id=tenant_id, nombre=nombre, estado=estado)
    db.add(tramite)
    db.commit()
    fijar_contexto_tenant(db, tenant_id)
    return tramite


def _limpiar(db, tenant_id):
    try:
        # Varios tests llaman a un endpoint que hace su propio `db.commit()`
        # (ej. `eliminar_tramite`) justo antes de este `finally` -- eso resetea
        # `app.tenant_id` (app/db/rls.py) y las DELETE de abajo, protegidas por
        # RLS, fallarían con "invalid input syntax for type uuid: ''" si no se
        # refija el contexto primero.
        fijar_contexto_tenant(db, tenant_id)
        db.execute(text("DELETE FROM accion_seguimiento WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM plan_modernizacion WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM diagnostico_tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# --- eliminar_tramite: borrado físico, solo pre-envío --------------------------


def test_eliminar_tramite_sin_diagnostico_borra_la_fila(caplog):
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        tramite = _preparar_tenant_y_tramite(db, tenant_id)
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")

        with caplog.at_level(logging.INFO, logger="diagmuni.auditoria"):
            resultado = eliminar_tramite(tramite.id, token, db)

        # eliminar_tramite ya hizo su propio commit (resetea app.tenant_id,
        # app/db/rls.py) -- refijar antes de la siguiente consulta con RLS en
        # esta misma sesión, mismo patrón que el resto del proyecto.
        fijar_contexto_tenant(db, tenant_id)
        assert resultado is None
        assert db.get(Tramite, tramite.id) is None

        [registro] = [r for r in caplog.records if r.name == "diagmuni.auditoria"]
        linea = json.loads(registro.message)
        assert linea["evento"] == "tramite_eliminado"
        assert linea["tramite_id"] == str(tramite.id)
        assert linea["nombre"] == tramite.nombre
    finally:
        _limpiar(db, tenant_id)


def test_eliminar_tramite_con_borrador_sin_enviar_borra_ambas_filas():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        tramite = _preparar_tenant_y_tramite(db, tenant_id, estado="en_progreso")
        diagnostico = DiagnosticoTramite(tenant_id=tenant_id, tramite_id=tramite.id, respuestas={"algo": "sin enviar"})
        db.add(diagnostico)
        db.commit()
        fijar_contexto_tenant(db, tenant_id)

        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        eliminar_tramite(tramite.id, token, db)
        fijar_contexto_tenant(db, tenant_id)

        assert db.get(Tramite, tramite.id) is None
        assert db.get(DiagnosticoTramite, diagnostico.id) is None
    finally:
        _limpiar(db, tenant_id)


def test_eliminar_tramite_con_diagnostico_enviado_rechaza_sin_borrar_nada():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        tramite = _preparar_tenant_y_tramite(db, tenant_id, estado="plan_listo")
        diagnostico = DiagnosticoTramite(
            tenant_id=tenant_id,
            tramite_id=tramite.id,
            respuestas={},
            indice_madurez=2,
            version_motor="1.0",
            completado_en=datetime.now(UTC),
        )
        db.add(diagnostico)
        db.commit()
        fijar_contexto_tenant(db, tenant_id)

        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")

        with pytest.raises(HTTPException) as exc_info:
            eliminar_tramite(tramite.id, token, db)
        assert exc_info.value.status_code == 409

        # Nada se tocó -- ni el tramite ni el diagnostico.
        assert db.get(Tramite, tramite.id) is not None
        assert db.get(DiagnosticoTramite, diagnostico.id) is not None
    finally:
        _limpiar(db, tenant_id)


def test_eliminar_tramite_inexistente_devuelve_404():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant vacío", clave=f"prueba-tram-vacio-{tenant_id}", pais="mx"))
        db.commit()
        fijar_contexto_tenant(db, tenant_id)

        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        with pytest.raises(HTTPException) as exc_info:
            eliminar_tramite(uuid4(), token, db)
        assert exc_info.value.status_code == 404
    finally:
        _limpiar(db, tenant_id)


# --- archivar_tramite / desarchivar_tramite: reversible, sin borrar nada -------


def test_archivar_y_desarchivar_tramite_ciclo_completo(caplog):
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        tramite = _preparar_tenant_y_tramite(db, tenant_id)
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")

        with caplog.at_level(logging.INFO, logger="diagmuni.auditoria"):
            resultado = archivar_tramite(tramite.id, token, db)
        assert resultado.archivado_en is not None
        eventos = [json.loads(r.message)["evento"] for r in caplog.records if r.name == "diagmuni.auditoria"]
        assert "tramite_archivado" in eventos

        db.refresh(tramite)
        assert tramite.archivado_en is not None

        # Ya archivado -> 409, no cambia nada.
        with pytest.raises(HTTPException) as exc_info:
            archivar_tramite(tramite.id, token, db)
        assert exc_info.value.status_code == 409

        caplog.clear()
        with caplog.at_level(logging.INFO, logger="diagmuni.auditoria"):
            resultado = desarchivar_tramite(tramite.id, token, db)
        assert resultado.archivado_en is None
        eventos = [json.loads(r.message)["evento"] for r in caplog.records if r.name == "diagmuni.auditoria"]
        assert "tramite_desarchivado" in eventos

        # Ya no está archivado -> 409 al desarchivar de nuevo.
        with pytest.raises(HTTPException) as exc_info:
            desarchivar_tramite(tramite.id, token, db)
        assert exc_info.value.status_code == 409
    finally:
        _limpiar(db, tenant_id)


def test_archivar_tramite_inexistente_devuelve_404():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant vacío", clave=f"prueba-tram-vacio2-{tenant_id}", pais="mx"))
        db.commit()
        fijar_contexto_tenant(db, tenant_id)

        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        with pytest.raises(HTTPException) as exc_info:
            archivar_tramite(uuid4(), token, db)
        assert exc_info.value.status_code == 404
    finally:
        _limpiar(db, tenant_id)


# --- Un trámite archivado sale del panel resumen (índice global incluido) -----


def test_tramite_archivado_no_infla_el_indice_global_ni_aparece_por_defecto():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        tramite_activo = _preparar_tenant_y_tramite(db, tenant_id, nombre="Activo", estado="plan_listo")
        db.add(
            DiagnosticoTramite(
                tenant_id=tenant_id,
                tramite_id=tramite_activo.id,
                respuestas={},
                indice_madurez=4,
                version_motor="1.0",
                completado_en=datetime.now(UTC),
            )
        )
        tramite_archivado = Tramite(tenant_id=tenant_id, nombre="A archivar", estado="plan_listo")
        db.add(tramite_archivado)
        db.commit()
        fijar_contexto_tenant(db, tenant_id)
        db.add(
            DiagnosticoTramite(
                tenant_id=tenant_id,
                tramite_id=tramite_archivado.id,
                respuestas={},
                # Índice bajo a propósito: si este trámite contaminara el índice
                # global tras archivarse, el promedio bajaría de forma detectable.
                indice_madurez=0,
                version_motor="1.0",
                completado_en=datetime.now(UTC),
            )
        )
        db.commit()
        fijar_contexto_tenant(db, tenant_id)

        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        archivar_tramite(tramite_archivado.id, token, db)

        panel = listar_tramites(token, db, BackgroundTasks())
        assert {t.nombre for t in panel.tramites} == {"Activo"}
        assert panel.indice_global == 4.0

        panel_archivados = listar_tramites(token, db, BackgroundTasks(), archivados=True)
        assert {t.nombre for t in panel_archivados.tramites} == {"A archivar"}
    finally:
        _limpiar(db, tenant_id)


def test_tramite_archivado_sale_de_seguimiento():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        tramite = _preparar_tenant_y_tramite(db, tenant_id, estado="plan_listo")
        diagnostico = DiagnosticoTramite(
            tenant_id=tenant_id,
            tramite_id=tramite.id,
            respuestas={},
            indice_madurez=2,
            version_motor="1.0",
            completado_en=datetime.now(UTC),
        )
        db.add(diagnostico)
        db.flush()
        plan = PlanModernizacion(
            tenant_id=tenant_id,
            diagnostico_tramite_id=diagnostico.id,
            version=1,
            modo="degradado",
            verificado=True,
            contenido={"resumen_narrativo": "x", "brechas": []},
        )
        db.add(plan)
        db.flush()
        accion = AccionSeguimiento(
            tenant_id=tenant_id,
            plan_modernizacion_id=plan.id,
            descripcion="Acción de prueba",
            responsable="Por asignar",
            fecha_objetivo=date.today() + timedelta(days=90),
        )
        db.add(accion)
        db.commit()
        fijar_contexto_tenant(db, tenant_id)

        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        assert any(a.tramite_id == tramite.id for a in listar_acciones(db))

        archivar_tramite(tramite.id, token, db)

        assert not any(a.tramite_id == tramite.id for a in listar_acciones(db))
    finally:
        _limpiar(db, tenant_id)

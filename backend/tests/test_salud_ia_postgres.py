"""Tests de `GET /api/admin/salud-ia/resumen` (app/adaptadores/http/admin_salud_ia.py)."""

import socket
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.adaptadores.http.admin_salud_ia import actualizar_proveedor, obtener_resumen_salud_ia
from app.adaptadores.http.deps import TokenData
from app.core.config import Settings, settings
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.models import DiagnosticoTramite, Job, PlanModernizacion, Tenant, Tramite
from app.schemas.salud_ia import ActualizarProveedorLlmRequest


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
def tenant_con_plan_y_job_fallido():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant salud IA", clave=f"prueba-salud-ia-{tenant_id}", pais="mx"))
        db.flush()
        tramite = Tramite(tenant_id=tenant_id, nombre="Trámite salud IA", estado="plan_listo")
        db.add(tramite)
        db.flush()
        diagnostico = DiagnosticoTramite(tenant_id=tenant_id, tramite_id=tramite.id, respuestas={})
        db.add(diagnostico)
        db.flush()
        db.add(
            PlanModernizacion(
                diagnostico_tramite_id=diagnostico.id, tenant_id=tenant_id, version=1, modo="llm",
                contenido={"resumen_narrativo": "x", "brechas": []}, verificado=True,
            )
        )
        db.add(Job(tenant_id=tenant_id, tipo="generacion_plan", diagnostico_tramite_id=diagnostico.id, estado="failed"))
        db.commit()
    finally:
        db.close()

    yield tenant_id

    db = abrir_sesion_tenant(tenant_id)
    try:
        db.execute(text("DELETE FROM job WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM plan_modernizacion WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM diagnostico_tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
        db.commit()
    finally:
        db.close()


def test_resumen_salud_ia_incluye_ultimo_plan_y_jobs_fallidos(tenant_con_plan_y_job_fallido):
    tenant_id = tenant_con_plan_y_job_fallido
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="admin_gobierno")
        resumen = obtener_resumen_salud_ia(token, db)

        assert resumen.ultimo_plan is not None
        assert resumen.ultimo_plan.modo == "llm"
        assert resumen.jobs_fallidos_24h == 1
        assert len(resumen.planes_recientes) == 1
    finally:
        db.close()


# --- BYOK: PATCH /api/admin/salud-ia/proveedor (app/aplicacion/preferencia_modelo_ia.py) ---


@pytest.fixture
def tenant_solo():
    """Tenant sin plan/job -- las pruebas de BYOK no necesitan esos datos, solo
    la fila de `tenant` para leer/escribir sus columnas de credencial."""
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant BYOK", clave=f"prueba-byok-{tenant_id}", pais="mx"))
        db.commit()
    finally:
        db.close()

    yield tenant_id

    db = abrir_sesion_tenant(tenant_id)
    try:
        db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
        db.commit()
    finally:
        db.close()


def test_resumen_sin_preferencia_devuelve_null_y_proveedores_disponibles(tenant_solo):
    db = abrir_sesion_tenant(tenant_solo)
    try:
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_solo, rol="admin_gobierno")
        resumen = obtener_resumen_salud_ia(token, db)

        assert resumen.proveedor_preferido is None
        assert set(resumen.proveedores_disponibles) == {"anthropic", "deepseek", "local"}
        assert resumen.deepseek_key_configurada is False
        assert resumen.anthropic_key_configurada is False
    finally:
        db.close()


def test_actualizar_preferencia_y_key_se_guardan_cifradas_y_no_se_devuelven_en_claro(tenant_solo):
    db = abrir_sesion_tenant(tenant_solo)
    try:
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_solo, rol="admin_gobierno")
        payload = ActualizarProveedorLlmRequest(proveedor="anthropic", anthropic_api_key="sk-real-del-gobierno")
        resumen = actualizar_proveedor(payload, token, db)

        assert resumen.proveedor_preferido == "anthropic"
        assert resumen.anthropic_key_configurada is True
        # La key NUNCA viaja en claro de vuelta -- solo el booleano de arriba.
        assert "sk-real-del-gobierno" not in resumen.model_dump_json()

        fijar_contexto_tenant(db, tenant_solo)
        tenant = db.get(Tenant, tenant_solo)
        assert tenant.anthropic_api_key_cifrada != "sk-real-del-gobierno"
    finally:
        db.close()


def test_actualizar_preferencia_invalida_responde_400(tenant_solo):
    """El router atrapa el ValueError de preferencia_modelo_ia.actualizar_preferencia
    y lo convierte en HTTPException 400 (admin_salud_ia.py) -- no debe escapar
    como ValueError crudo."""
    db = abrir_sesion_tenant(tenant_solo)
    try:
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_solo, rol="admin_gobierno")
        payload = ActualizarProveedorLlmRequest(proveedor="openai")
        with pytest.raises(HTTPException) as exc_info:
            actualizar_proveedor(payload, token, db)
        assert exc_info.value.status_code == 400
    finally:
        db.close()


def test_campo_omitido_no_borra_la_credencial_ya_guardada(tenant_solo):
    db = abrir_sesion_tenant(tenant_solo)
    try:
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_solo, rol="admin_gobierno")
        actualizar_proveedor(
            ActualizarProveedorLlmRequest(proveedor="anthropic", anthropic_api_key="sk-real-del-gobierno"),
            token,
            db,
        )
        # Segundo PATCH solo cambia el proveedor -- `anthropic_api_key` ni
        # siquiera se manda (queda fuera de `exclude_unset`), la credencial ya
        # guardada debe sobrevivir intacta.
        resumen = actualizar_proveedor(ActualizarProveedorLlmRequest(proveedor="deepseek"), token, db)

        assert resumen.proveedor_preferido == "deepseek"
        assert resumen.anthropic_key_configurada is True
    finally:
        db.close()


def test_campo_vacio_borra_la_credencial_guardada(tenant_solo):
    db = abrir_sesion_tenant(tenant_solo)
    try:
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_solo, rol="admin_gobierno")
        actualizar_proveedor(
            ActualizarProveedorLlmRequest(proveedor="anthropic", anthropic_api_key="sk-real-del-gobierno"),
            token,
            db,
        )
        resumen = actualizar_proveedor(ActualizarProveedorLlmRequest(anthropic_api_key=""), token, db)

        assert resumen.anthropic_key_configurada is False
    finally:
        db.close()


def test_proveedor_activo_refleja_el_override_del_tenant_sobre_llm_provider_global(tenant_solo, monkeypatch):
    monkeypatch.setattr(
        "app.adaptadores.llm.config.settings_global", Settings(llm_provider="deepseek")
    )
    db = abrir_sesion_tenant(tenant_solo)
    try:
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_solo, rol="admin_gobierno")
        resumen = actualizar_proveedor(ActualizarProveedorLlmRequest(proveedor="anthropic"), token, db)

        assert resumen.proveedor_activo == "anthropic"
    finally:
        db.close()

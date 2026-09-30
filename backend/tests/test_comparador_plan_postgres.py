"""Tests de los endpoints del comparador de versiones (`GET .../plan/versiones`
y `GET .../plan/versiones/{version}`, app/adaptadores/http/planes.py)."""

import socket
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.adaptadores.http.deps import TokenData
from app.adaptadores.http.planes import listar_versiones_plan, obtener_version_plan
from app.core.config import settings
from app.db.rls import abrir_sesion_tenant
from app.models import DiagnosticoTramite, PlanModernizacion, Tenant, Tramite


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


def _brecha(variable: str) -> dict:
    return {
        "variable": variable,
        "narrativa": f"narrativa de {variable}",
        "paso_administrativo": "paso",
        "paso_tecnico": "paso",
        "paso_organizacional": "paso",
        "prerrequisitos": [],
        "por_que_importa": "importa",
        "fuente_normativa": "fuente",
        "categoria_catalogo": "categoria",
        "componente_recomendado": None,
    }


@pytest.fixture
def tramite_con_dos_versiones():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant comparador", clave=f"prueba-comparador-{tenant_id}", pais="mx"))
        db.flush()
        tramite = Tramite(tenant_id=tenant_id, nombre="Trámite comparador", estado="plan_listo")
        db.add(tramite)
        db.flush()
        diagnostico = DiagnosticoTramite(
            tenant_id=tenant_id, tramite_id=tramite.id, respuestas={}, indice_madurez=2
        )
        db.add(diagnostico)
        db.flush()

        contenido_v1 = {
            "resumen_narrativo": "v1",
            "brechas": [_brecha("firma_electronica_habilitada"), _brecha("motor_pagos")],
        }
        contenido_v2 = {"resumen_narrativo": "v2", "brechas": [_brecha("motor_pagos"), _brecha("interoperabilidad")]}
        db.add(
            PlanModernizacion(
                diagnostico_tramite_id=diagnostico.id, tenant_id=tenant_id, version=1, modo="degradado",
                contenido=contenido_v1, verificado=True,
            )
        )
        db.add(
            PlanModernizacion(
                diagnostico_tramite_id=diagnostico.id, tenant_id=tenant_id, version=2, modo="llm",
                contenido=contenido_v2, verificado=True,
            )
        )
        db.commit()
        tramite_id = tramite.id
    finally:
        db.close()

    yield tenant_id, tramite_id

    db = abrir_sesion_tenant(tenant_id)
    try:
        db.execute(text("DELETE FROM plan_modernizacion WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM diagnostico_tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tramite WHERE tenant_id = :t"), {"t": str(tenant_id)})
        db.execute(text("DELETE FROM tenant WHERE id = :t"), {"t": str(tenant_id)})
        db.commit()
    finally:
        db.close()


def test_listar_versiones_ordenadas_mas_reciente_primero(tramite_con_dos_versiones):
    tenant_id, tramite_id = tramite_con_dos_versiones
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        versiones = listar_versiones_plan(tramite_id, token, db)
        assert [v.version for v in versiones] == [2, 1]
        assert versiones[0].modo == "llm"
        assert versiones[0].brechas_totales == 2
    finally:
        db.close()


def test_obtener_version_especifica_trae_su_propio_contenido(tramite_con_dos_versiones):
    tenant_id, tramite_id = tramite_con_dos_versiones
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        v1 = obtener_version_plan(tramite_id, 1, token, db)
        assert v1.modo == "degradado"
        variables_v1 = {b["variable"] for b in v1.contenido["brechas"]}
        assert variables_v1 == {"firma_electronica_habilitada", "motor_pagos"}
    finally:
        db.close()


def test_obtener_version_inexistente_404(tramite_con_dos_versiones):
    tenant_id, tramite_id = tramite_con_dos_versiones
    db = abrir_sesion_tenant(tenant_id)
    try:
        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        with pytest.raises(HTTPException) as exc_info:
            obtener_version_plan(tramite_id, 99, token, db)
        assert exc_info.value.status_code == 404
    finally:
        db.close()

"""Tests de las funciones puras de `app/api/seguimiento.py` -- sin sesión de DB
real (mismo criterio documentado en test_api_planes.py y test_plan_job.py).

`_ids_planes_vigentes` es la pieza que decide qué acciones se muestran al
regenerar un plan (segunda versión): cubre el caso que pide la tarea -- que las
acciones de la versión anterior queden fuera del listado.

Al final del archivo hay un test de integración distinto de los de arriba: ejercita
`actualizar_accion` completo contra Postgres real (RLS incluido), no una sesión
espía -- ver docstring de `test_actualizar_accion_no_revienta_rls_tras_commit_contra_postgres_real`
para el porqué.
"""

import socket
from datetime import UTC, date, datetime
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.api.deps import TokenData
from app.api.seguimiento import _construir_accion_out, _ids_planes_vigentes, actualizar_accion
from app.core.config import settings
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.models import AccionSeguimiento, DiagnosticoTramite, PlanModernizacion, Tenant, Tramite
from app.schemas.accion_seguimiento import AccionSeguimientoActualizar


def test_ids_planes_vigentes_excluye_version_anterior_del_mismo_diagnostico():
    diagnostico_id = uuid4()
    plan_v1, plan_v2 = uuid4(), uuid4()

    vigentes = _ids_planes_vigentes([(plan_v1, diagnostico_id, 1), (plan_v2, diagnostico_id, 2)])

    assert vigentes == {plan_v2}


def test_ids_planes_vigentes_admite_varios_diagnosticos_independientes():
    diagnostico_a, diagnostico_b = uuid4(), uuid4()
    plan_a_v1, plan_a_v2 = uuid4(), uuid4()
    plan_b_v1 = uuid4()

    vigentes = _ids_planes_vigentes(
        [
            (plan_a_v1, diagnostico_a, 1),
            (plan_a_v2, diagnostico_a, 2),
            (plan_b_v1, diagnostico_b, 1),
        ]
    )

    assert vigentes == {plan_a_v2, plan_b_v1}


def test_ids_planes_vigentes_lista_vacia():
    assert _ids_planes_vigentes([]) == set()


def test_construir_accion_out_agrega_tramite_id_y_nombre():
    tramite_id = uuid4()
    accion = AccionSeguimiento(
        id=uuid4(),
        plan_modernizacion_id=uuid4(),
        tenant_id=uuid4(),
        descripcion="Digitalizar el formulario del trámite",
        responsable="Por asignar",
        fecha_objetivo=date(2026, 11, 3),
        estado_semaforo="en_progreso",
        actualizado_en=datetime.now(UTC),
    )

    resultado = _construir_accion_out(accion, tramite_id, "Licencia de funcionamiento")

    assert resultado.tramite_id == tramite_id
    assert resultado.tramite_nombre == "Licencia de funcionamiento"
    assert resultado.descripcion == "Digitalizar el formulario del trámite"
    assert resultado.responsable == "Por asignar"
    assert resultado.estado_semaforo == "en_progreso"


# --- `actualizar_accion` contra Postgres real (RLS incluido) --------------------
#
# Bug real detectado en producción: `db.commit()` termina la transacción y con
# ella el `app.tenant_id` local fijado con `set_config(..., is_local=true)` (ver
# app/db/rls.py) -- cualquier consulta posterior en la misma sesión (acá,
# `db.refresh` y `_tramite_de_plan`) revienta con
# `InvalidTextRepresentation: invalid input syntax for type uuid: ""` porque la
# policy RLS evalúa `current_setting('app.tenant_id')` contra un valor ya vacío.
#
# Una sesión espía (como la de test_plan_job.py) no lo hubiera detectado: ese
# patrón verifica el ORDEN de las llamadas mockeadas, no que Postgres realmente
# vuelva a aceptar una consulta con RLS después del commit. Por eso este test
# habla con Postgres real -- se salta limpio (no falla) si no hay uno alcanzable
# con el `DATABASE_URL` configurado (CI no provisiona Postgres para esta suite,
# ver .github/workflows/ci.yml), pero corriendo contra `docker compose up db`
# ejercita el problema de verdad.


def _postgres_real_disponible() -> bool:
    """Chequeo de dos pasos: primero un `connect` de socket con timeout corto (el
    driver de Postgres no aplica ninguno por defecto -- sin esto, apuntar a un host
    inalcanzable puede colgar la recolección de pytest en vez de saltar el test)."""
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
def test_actualizar_accion_no_revienta_rls_tras_commit_contra_postgres_real():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant de prueba RLS", clave=f"prueba-rls-{tenant_id}", pais="mx"))
        db.flush()

        tramite = Tramite(tenant_id=tenant_id, nombre="Trámite de prueba RLS", estado="plan_listo")
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
            contenido={"resumen_narrativo": "resumen de prueba", "brechas": []},
            verificado=True,
        )
        db.add(plan)
        db.flush()

        accion = AccionSeguimiento(
            plan_modernizacion_id=plan.id,
            tenant_id=tenant_id,
            descripcion="Acción de prueba RLS",
            responsable="Por asignar",
            fecha_objetivo=date(2026, 12, 1),
        )
        db.add(accion)
        db.commit()
        # mismo commit intermedio del propio setup del test -- también resetea el
        # contexto, hay que refijarlo antes de que `actualizar_accion` haga su
        # primer `db.get`.
        fijar_contexto_tenant(db, tenant_id)

        token = TokenData(usuario_id=uuid4(), tenant_id=tenant_id, rol="funcionario")
        payload = AccionSeguimientoActualizar(responsable="Nuevo responsable tras el fix")

        resultado = actualizar_accion(accion.id, payload, token, db)

        assert resultado.responsable == "Nuevo responsable tras el fix"
        assert resultado.tramite_id == tramite.id
        assert resultado.tramite_nombre == "Trámite de prueba RLS"
    finally:
        # limpieza explícita: hubo commits reales, un rollback no alcanza para
        # deshacerlos. El contexto de tenant ya quedó fijado por la última llamada
        # a `fijar_contexto_tenant` dentro de `actualizar_accion`.
        try:
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

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
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select, text

from app.api.deps import TokenData
from app.api.diagnosticos import enviar_diagnostico, guardar_diagnostico
from app.core.config import settings
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.models import DiagnosticoTramite, Job, Tenant, Tramite
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


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_enviar_diagnostico_repetido_con_job_pendiente_rechaza_con_409_sin_perder_respuestas():
    """Auditoría de seguridad H-11: sin este chequeo, llamar el endpoint varias
    veces seguidas sobre el mismo trámite creaba un job y una versión de plan
    nuevos por cada llamada -- sin límite. Ahora, con el primer job todavía
    `pending` (no se llegó a llamar `ejecutar_generacion_plan`, que es lo que lo
    pasa a `running`/`done`), un segundo envío se rechaza con 409.

    Regresión cubierta a propósito: una versión intermedia de este chequeo hacía
    `return diagnostico` en este caso, o sea respondía 200 y descartaba en
    silencio las respuestas del segundo envío. El funcionario que corregía una
    respuesta mal capturada mientras el plan se generaba veía "guardado" y
    perdía la corrección. El 409 obliga a que el cliente conserve su captura, y
    acá se verifica además que la fila no quedó a medio escribir."""
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

        enviar_diagnostico(tramite.id, payload, token, db, BackgroundTasks())

        jobs_antes = db.execute(select(Job).where(Job.diagnostico_tramite_id.isnot(None))).scalars().all()
        cantidad_antes = len([j for j in jobs_antes if j.tenant_id == tenant_id])

        # segundo envío con respuestas DISTINTAS: debe rechazarse sin escribir nada
        payload_corregido = DiagnosticoEnviar(
            respuestas={**payload.respuestas, "motor_pagos": False, "firma_electronica_habilitada": False}
        )
        with pytest.raises(HTTPException) as excinfo:
            enviar_diagnostico(tramite.id, payload_corregido, token, db, BackgroundTasks())
        assert excinfo.value.status_code == 409
        fijar_contexto_tenant(db, tenant_id)

        jobs_despues = db.execute(select(Job).where(Job.diagnostico_tramite_id.isnot(None))).scalars().all()
        cantidad_despues = len([j for j in jobs_despues if j.tenant_id == tenant_id])
        assert cantidad_despues == cantidad_antes

        # y la fila sigue con las respuestas del primer envío, no a medio camino
        db.expire_all()
        diagnostico = db.execute(
            select(DiagnosticoTramite).where(DiagnosticoTramite.tenant_id == tenant_id)
        ).scalar_one()
        fijar_contexto_tenant(db, tenant_id)
        assert diagnostico.respuestas["motor_pagos"] is True
        assert diagnostico.respuestas["firma_electronica_habilitada"] is True
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


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_enviar_diagnostico_con_job_pending_obsoleto_lo_redispara_contra_postgres_real():
    """Un job puede quedar `pending` para siempre si el proceso muere justo tras
    crear el job y antes de que corra el BackgroundTask (nunca llega a `running`).
    Pasado `settings.job_umbral_obsoleto_minutos`, un nuevo envío debe redisparar
    ese mismo job (no crear uno nuevo, no bloquear la respuesta)."""
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

        enviar_diagnostico(tramite.id, payload, token, db, BackgroundTasks())
        job_original = db.execute(select(Job).where(Job.tenant_id == tenant_id)).scalar_one()

        # simula que el job nunca arrancó y ya pasó el umbral de obsolescencia
        db.execute(
            text("UPDATE job SET updated_at = now() - interval '1 hour' WHERE id = :id"),
            {"id": str(job_original.id)},
        )
        db.commit()
        fijar_contexto_tenant(db, tenant_id)
        # el UPDATE de arriba fue SQL crudo -- el objeto ya cargado en la sesión
        # sigue con el `updated_at` viejo en memoria hasta que se expira.
        db.expire(job_original)

        resultado = enviar_diagnostico(tramite.id, payload, token, db, BackgroundTasks())
        assert resultado.id is not None

        jobs = db.execute(select(Job).where(Job.tenant_id == tenant_id)).scalars().all()
        assert len(jobs) == 1
        assert jobs[0].id == job_original.id
        assert jobs[0].intentos == 1
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


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_enviar_diagnostico_excede_cooldown_responde_429_contra_postgres_real():
    """Auditoría de seguridad H-11 (segunda mitad): el chequeo de job vigente no
    protege una vez que el job anterior ya terminó -- este cooldown acota cuántas
    generaciones nuevas puede disparar el mismo usuario en la ventana."""
    from app.api import diagnosticos as diagnosticos_api

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

        # los envíos 2..N sobre el mismo trámite chocan con el 409 del job en
        # curso, pero consumen cupo del cooldown igual -- lo que se mide acá.
        for _ in range(diagnosticos_api.INTENTOS_MAXIMOS_POR_TRAMITE):
            try:
                enviar_diagnostico(tramite.id, payload, token, db, BackgroundTasks())
            except HTTPException as e:
                assert e.status_code == 409
            fijar_contexto_tenant(db, tenant_id)

        with pytest.raises(HTTPException) as excinfo:
            enviar_diagnostico(tramite.id, payload, token, db, BackgroundTasks())
        assert excinfo.value.status_code == 429
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


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_enviar_diagnostico_de_varios_tramites_distintos_no_choca_con_el_cooldown():
    """El cooldown de H-11 tiene que acotar la regeneración de UN mismo trámite,
    no la captura del catálogo. Llavearlo solo por `usuario_id` rompía el flujo
    central del producto: un funcionario que envía el diagnóstico de los trámites
    de su municipio (decenas, cada uno un envío legítimo) topaba con un 429 al
    sexto trámite distinto. Se envían más trámites que `INTENTOS_MAXIMOS_POR_TRAMITE`
    para que la regresión reaparezca si la llave vuelve a ser solo el usuario."""
    from app.api import diagnosticos as diagnosticos_api

    cantidad = diagnosticos_api.INTENTOS_MAXIMOS_POR_TRAMITE + 3
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant de prueba diagnostico", clave=f"prueba-diag-{tenant_id}", pais="mx"))
        db.flush()

        tramites = [
            Tramite(tenant_id=tenant_id, nombre=f"Trámite de prueba {i}", estado="diagnosticado")
            for i in range(cantidad)
        ]
        for tramite in tramites:
            db.add(tramite)
        db.commit()
        fijar_contexto_tenant(db, tenant_id)
        tramite_ids = [tramite.id for tramite in tramites]

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

        for tramite_id in tramite_ids:
            enviar_diagnostico(tramite_id, payload, token, db, BackgroundTasks())
            fijar_contexto_tenant(db, tenant_id)

        jobs = db.execute(select(Job).where(Job.tenant_id == tenant_id)).scalars().all()
        assert len(jobs) == cantidad
    finally:
        try:
            db.execute(text("DELETE FROM accion_seguimiento WHERE tenant_id = :t"), {"t": str(tenant_id)})
            db.execute(text("DELETE FROM plan_modernizacion WHERE tenant_id = :t"), {"t": str(tenant_id)})
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


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_enviar_diagnostico_respeta_el_techo_por_usuario(monkeypatch):
    """La llave por trámite sola no acota el total: un script recorriendo muchos
    trámites distintos dispararía una generación por cada uno. El techo por
    usuario existe para eso. Se monkeypatchea a 2 para no tener que hacer
    `INTENTOS_MAXIMOS_POR_USUARIO` envíos reales contra Postgres."""
    from app.api import diagnosticos as diagnosticos_api
    from app.core.rate_limit import LimitadorVentanaDeslizante

    monkeypatch.setattr(
        diagnosticos_api,
        "_limitador_usuario",
        LimitadorVentanaDeslizante(2, diagnosticos_api.VENTANA_SEGUNDOS),
    )

    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant de prueba diagnostico", clave=f"prueba-diag-{tenant_id}", pais="mx"))
        db.flush()

        tramites = [
            Tramite(tenant_id=tenant_id, nombre=f"Trámite de prueba techo {i}", estado="diagnosticado")
            for i in range(3)
        ]
        for tramite in tramites:
            db.add(tramite)
        db.commit()
        fijar_contexto_tenant(db, tenant_id)
        tramite_ids = [tramite.id for tramite in tramites]

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

        for tramite_id in tramite_ids[:2]:
            enviar_diagnostico(tramite_id, payload, token, db, BackgroundTasks())
            fijar_contexto_tenant(db, tenant_id)

        with pytest.raises(HTTPException) as excinfo:
            enviar_diagnostico(tramite_ids[2], payload, token, db, BackgroundTasks())
        assert excinfo.value.status_code == 429
    finally:
        try:
            db.execute(text("DELETE FROM accion_seguimiento WHERE tenant_id = :t"), {"t": str(tenant_id)})
            db.execute(text("DELETE FROM plan_modernizacion WHERE tenant_id = :t"), {"t": str(tenant_id)})
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

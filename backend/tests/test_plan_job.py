"""Tests de `_generar_contenido_y_modo`, la función pura de `app/jobs/plan_job.py`
que decide qué contenido y modo persiste `ejecutar_generacion_plan`.

No requieren base de datos real -- eso no se toca ni se testea acá. Se mockea
`litellm.completion`, nunca red real. Son tests de integración entre `plan_job`,
`generador_plan` y `verificador` (mockeando solo en el límite de red/config), no
`verificar_contenido` -- así se ejercita la cadena real de decisión, no una
simulación de su resultado.

Nota técnica: `generador_plan` y `verificador` hacen `import litellm` por separado,
pero es el mismo objeto módulo en el proceso -- `generador_plan.litellm is
verificador.litellm`. Por eso el mock de `completion` es UNA sola función que
distingue la llamada de redacción (E2) de la de auditoría (E3) inspeccionando el
prompt, en vez de dos `monkeypatch.setattr` independientes que se pisarían entre sí.
"""

import socket
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text

from app.core.config import settings
from app.db.rls import abrir_sesion_tenant, fijar_contexto_tenant
from app.engine.plantillas import generar_contenido_degradado
from app.ia import generador_plan, verificador
from app.jobs import plan_job
from app.models import AccionSeguimiento, DiagnosticoTramite, Job, PlanModernizacion, Tenant, Tramite

RESPUESTAS_CON_BRECHAS = {
    "documentos_digitalizados": False,
    "motor_pagos": False,
    "firma_electronica_habilitada": False,
    "interoperabilidad": False,
    "proteccion_datos_incompleta": True,
    "mecanismo_identidad": "ninguno",
}


def _mock_respuesta(texto: str) -> dict:
    return {"choices": [{"message": {"content": texto}}]}


def _mockear_generacion_exitosa(monkeypatch, narrativa: str = "prosa redactada por el mock de Claude") -> None:
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test-calidad")
    monkeypatch.setattr(generador_plan.litellm, "completion", lambda *a, **k: _mock_respuesta(narrativa))


def _mockear_ruta_llm_disponible(monkeypatch) -> None:
    """Fija `obtener_rutas_generacion` para que estos tests no dependan de qué
    variables de entorno reales (LLM_PROVIDER/OLLAMA_API_BASE) tenga el proceso
    que corre la suite -- la disponibilidad la controla `esta_disponible`
    monkeypateado, no la resolución real de proveedor. `plan_job` y `generador_plan`
    importan `obtener_rutas_generacion` cada uno por su cuenta (dos nombres de
    módulo distintos) -- hay que fijar ambas copias, no una sola."""
    monkeypatch.setattr(plan_job, "obtener_rutas_generacion", lambda: ["calidad", "calidad_respaldo", "local"])
    monkeypatch.setattr(generador_plan, "obtener_rutas_generacion", lambda: ["calidad", "calidad_respaldo", "local"])


def _mockear_completion_combinado(monkeypatch, narrativa: str, veredicto: str) -> None:
    """Un solo mock de `litellm.completion` (mismo objeto módulo en `generador_plan`
    y en `verificador`, ver nota del módulo) que responde `narrativa` a la llamada
    de redacción (E2) y `veredicto` a la llamada de auditoría (E3), distinguiéndolas
    por el prompt -- el prompt de `verificador.py` pide explícitamente "SI"/"NO"."""

    def _completion(*args, **kwargs):
        prompt = kwargs["messages"][0]["content"]
        if "auditor de fidelidad" in prompt:
            return _mock_respuesta(veredicto)
        return _mock_respuesta(narrativa)

    monkeypatch.setattr(generador_plan.litellm, "completion", _completion)


# --- (a) ruta "calidad" no disponible -> degradado, SIN llamar nunca al verificador ---


def test_calidad_no_disponible_va_directo_a_degradado_sin_llamar_verificador(monkeypatch):
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: False)

    def _verificar_no_debe_llamarse(*args, **kwargs):
        raise AssertionError("verificar_contenido no debía invocarse sin ruta 'calidad' disponible")

    monkeypatch.setattr(plan_job, "verificar_contenido", _verificar_no_debe_llamarse)

    def _generar_llm_no_debe_llamarse(*args, **kwargs):
        raise AssertionError("generar_contenido_llm no debía invocarse sin ruta 'calidad' disponible")

    monkeypatch.setattr(plan_job, "generar_contenido_llm", _generar_llm_no_debe_llamarse)

    modo, contenido, verificado = plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx")

    assert modo == "degradado"
    assert verificado is True
    assert contenido == generar_contenido_degradado(RESPUESTAS_CON_BRECHAS, "mx")


# --- (b) verificación exitosa -> modo llm, verificado=True ----------------------


def test_verificacion_exitosa_persiste_modo_llm(monkeypatch):
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: True)
    _mockear_ruta_llm_disponible(monkeypatch)
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test-calidad")
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test-economico")
    _mockear_completion_combinado(
        monkeypatch, narrativa="prosa redactada por el mock de Claude", veredicto="SI"
    )

    modo, contenido, verificado = plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx")

    assert modo == "llm"
    assert verificado is True
    assert len(contenido["brechas"]) > 0
    for brecha in contenido["brechas"]:
        assert brecha["narrativa"] == "prosa redactada por el mock de Claude"


# --- (c) verificación fallida (el auditor responde NO) -> degradado, verificado=True ---


def test_verificacion_fallida_cae_a_degradado(monkeypatch):
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: True)
    _mockear_ruta_llm_disponible(monkeypatch)
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test-calidad")
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test-economico")
    _mockear_completion_combinado(
        monkeypatch, narrativa="prosa redactada por el mock de Claude", veredicto="NO"
    )

    modo, contenido, verificado = plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx")

    assert modo == "degradado"
    assert verificado is True
    assert contenido == generar_contenido_degradado(RESPUESTAS_CON_BRECHAS, "mx")


# --- (d) verificador sin "economico" (sin key), contenido fiel -> modo llm igual ---
#
# Cambio de comportamiento deliberado (docs/plan-implementacion-e1-bis-capa-ia-local.md
# sección 9): antes, sin ninguna ruta de verificación LLM disponible, esto degradaba
# siempre -- el modo llm 100% local (sin ninguna API de pago) quedaba inalcanzable.
# Ahora la compuerta determinista de `verificador_citas.py` (sin citas/números
# fabricados) basta por sí sola para `verificado=true`, sin llamar a ningún LLM.


def test_verificador_sin_economico_contenido_fiel_persiste_modo_llm(monkeypatch):
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: True)
    _mockear_ruta_llm_disponible(monkeypatch)
    _mockear_generacion_exitosa(monkeypatch)

    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: False)

    llamadas_auditoria = []

    def _completion_espia(*args, **kwargs):
        prompt = kwargs["messages"][0]["content"]
        if "auditor de fidelidad" in prompt:
            llamadas_auditoria.append(kwargs)
        return _mock_respuesta("prosa redactada por el mock de Claude")

    monkeypatch.setattr(verificador.litellm, "completion", _completion_espia)

    modo, contenido, verificado = plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx")

    assert llamadas_auditoria == []  # la compuerta determinista nunca necesitó auditar con LLM
    assert modo == "llm"
    assert verificado is True
    for brecha in contenido["brechas"]:
        assert brecha["narrativa"] == "prosa redactada por el mock de Claude"


def test_verificador_sin_economico_contenido_con_cita_inventada_cae_a_degradado(monkeypatch):
    """Misma ausencia de `economico` que el test anterior, pero la narrativa
    generada trae una cita fabricada -- la compuerta determinista rechaza sin
    necesitar ningún LLM disponible para contradecirla."""
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: True)
    _mockear_ruta_llm_disponible(monkeypatch)
    narrativa_con_cita_inventada = (
        "Este trámite debe completarse conforme al Artículo 999 de la Ley Federal "
        "de Trámites Digitales, dentro de un plazo máximo de 10 días naturales."
    )
    _mockear_generacion_exitosa(monkeypatch, narrativa=narrativa_con_cita_inventada)

    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: False)

    def _completion_no_debe_auditar(*args, **kwargs):
        prompt = kwargs["messages"][0]["content"]
        if "auditor de fidelidad" in prompt:
            raise AssertionError("no debía intentar auditar con LLM sin economico disponible")
        return _mock_respuesta(narrativa_con_cita_inventada)

    monkeypatch.setattr(verificador.litellm, "completion", _completion_no_debe_auditar)

    modo, contenido, verificado = plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx")

    assert modo == "degradado"
    assert verificado is True
    assert contenido == generar_contenido_degradado(RESPUESTAS_CON_BRECHAS, "mx")


# --- (e) el verificador lanza una excepción (timeout/red) -> degradado, verificado=True ---


def test_verificador_lanza_excepcion_cae_a_degradado(monkeypatch):
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: True)
    _mockear_ruta_llm_disponible(monkeypatch)
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test-calidad")
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test-economico")

    def _completion(*args, **kwargs):
        prompt = kwargs["messages"][0]["content"]
        if "auditor de fidelidad" in prompt:
            raise TimeoutError("simulated timeout")
        return _mock_respuesta("prosa redactada por el mock de Claude")

    monkeypatch.setattr(generador_plan.litellm, "completion", _completion)

    modo, contenido, verificado = plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx")

    assert modo == "degradado"
    assert verificado is True
    assert contenido == generar_contenido_degradado(RESPUESTAS_CON_BRECHAS, "mx")


# --- (f) nunca se produce verificado=False en ningún camino ---------------------


def test_verificado_nunca_es_false(monkeypatch):
    escenarios = []

    # calidad no disponible
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: False)
    escenarios.append(plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx"))

    # calidad disponible, verificador aprueba
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: True)
    _mockear_ruta_llm_disponible(monkeypatch)
    monkeypatch.setattr(generador_plan, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(generador_plan, "api_key_de", lambda ruta: "sk-test")
    monkeypatch.setattr(verificador, "esta_disponible", lambda ruta: True)
    monkeypatch.setattr(verificador, "api_key_de", lambda ruta: "sk-test")
    _mockear_completion_combinado(monkeypatch, narrativa="prosa mock", veredicto="SI")
    escenarios.append(plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx"))

    # calidad disponible, verificador rechaza
    _mockear_completion_combinado(monkeypatch, narrativa="prosa mock", veredicto="NO")
    escenarios.append(plan_job._generar_contenido_y_modo(RESPUESTAS_CON_BRECHAS, "mx"))

    for _modo, _contenido, verificado in escenarios:
        assert verificado is True


# --- `_esta_obsoleto` -- watchdog de jobs `running` sin actualizar (sin DB real) ---
#
# `revisar_job_obsoleto` y `_persistir_plan_degradado` sí necesitan una sesión real
# (db.get/db.execute contra tablas con RLS) -- no se testean acá, no existe
# infraestructura de DB real en el repo. Solo se ejercita la parte pura: el cálculo
# de staleness. El resto queda verificado por lectura de código.
#
# Los tests de `revisar_job_obsoleto` más abajo cubren que `plan_job.py` invoca
# `fijar_contexto_tenant` la cantidad correcta de veces tras cada `db.commit()` --
# con una sesión espía, sin Postgres real. Que el contexto de tenant efectivamente
# se vuelva a fijar a nivel de RLS en Postgres queda pendiente de confirmar contra
# una instancia real.


def test_esta_obsoleto_false_si_se_actualizo_hace_poco():
    ahora = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)
    actualizado_en = ahora - timedelta(minutes=5)

    assert plan_job._esta_obsoleto(actualizado_en, umbral_minutos=15, ahora=ahora) is False


def test_esta_obsoleto_true_si_supera_el_umbral():
    ahora = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)
    actualizado_en = ahora - timedelta(minutes=16)

    assert plan_job._esta_obsoleto(actualizado_en, umbral_minutos=15, ahora=ahora) is True


def test_esta_obsoleto_false_justo_en_el_umbral():
    ahora = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)
    actualizado_en = ahora - timedelta(minutes=15)

    assert plan_job._esta_obsoleto(actualizado_en, umbral_minutos=15, ahora=ahora) is False


def test_esta_obsoleto_admite_datetime_naive():
    """Postgres puede devolver `updated_at` sin tzinfo -- no debe explotar al
    restarlo contra un `datetime` aware."""
    ahora = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)
    actualizado_en_naive = datetime(2026, 7, 31, 11, 30)  # sin tzinfo, 30 min antes

    assert plan_job._esta_obsoleto(actualizado_en_naive, umbral_minutos=15, ahora=ahora) is True


# --- `revisar_job_obsoleto` -- vuelve a fijar el contexto de tenant tras cada commit ---
#
# `db.execute`/`db.get` reales (adentro de `_persistir_plan_degradado`) se mockean
# directamente en `plan_job`, no se simulan con una sesión falsa -- eso ya está
# fuera de alcance acá (ver nota arriba). Lo que se ejercita es que
# `revisar_job_obsoleto`, tras cada uno de sus `db.commit()`, llama a
# `fijar_contexto_tenant` exactamente una vez y en ese orden.

_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
_DIAGNOSTICO_ID = UUID("00000000-0000-0000-0000-000000000002")


class _ResultadoFalso:
    """`db.execute(...)` solo se usa acá para leer `version_previa` vía
    `scalar_one_or_none()` -- no hace falta simular ningún otro método de `Result`."""

    def __init__(self, valor: object) -> None:
        self._valor = valor

    def scalar_one_or_none(self) -> object:
        return self._valor


class _SesionEspia:
    """Sesión mínima que registra `commit` -- extendida (sin cambiar el uso existente
    en los tests de `revisar_job_obsoleto` de este archivo, que solo pasan `orden`)
    para registrar `.add()` y admitir `.get()`/`.execute()`/`.flush()`/`.close()` como
    no-op o devolviendo los objetos de prueba fijados en el constructor -- suficiente
    para ejercitar `_persistir_plan_degradado` y `ejecutar_generacion_plan` completos
    sin ninguna infraestructura de Postgres real."""

    def __init__(
        self,
        orden: list[str],
        *,
        job: object | None = None,
        diagnostico: DiagnosticoTramite | None = None,
        tenant: Tenant | None = None,
        tramite: Tramite | None = None,
        version_previa: int | None = None,
    ) -> None:
        self._orden = orden
        self.agregados: list[object] = []
        self._job = job
        self._diagnostico = diagnostico
        self._tenant = tenant
        self._tramite = tramite
        self._version_previa = version_previa

    def commit(self) -> None:
        self._orden.append("commit")

    def rollback(self) -> None:
        self._orden.append("rollback")

    def add(self, obj: object) -> None:
        self.agregados.append(obj)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass

    def get(self, modelo: type, _id: object) -> object:
        if modelo is Job:
            return self._job
        if modelo is DiagnosticoTramite:
            return self._diagnostico
        if modelo is Tenant:
            return self._tenant
        if modelo is Tramite:
            return self._tramite
        raise AssertionError(f"get inesperado en la sesión de prueba: {modelo}")

    def execute(self, _stmt: object) -> _ResultadoFalso:
        return _ResultadoFalso(self._version_previa)


class _JobFalso:
    def __init__(self, estado: str, intentos: int, updated_at: datetime | None = None) -> None:
        self.estado = estado
        self.intentos = intentos
        self.diagnostico_tramite_id = _DIAGNOSTICO_ID
        self.updated_at = updated_at


def _espiar_fijar_contexto_tenant(monkeypatch, orden: list[str]) -> None:
    def _fijar_contexto_espia(db, tenant_id) -> None:
        assert tenant_id == _TENANT_ID
        orden.append("fijar_contexto_tenant")

    monkeypatch.setattr(plan_job, "fijar_contexto_tenant", _fijar_contexto_espia)


def test_revisar_job_obsoleto_failed_con_limite_agotado_refija_contexto_tenant(monkeypatch):
    monkeypatch.setattr(plan_job, "_persistir_plan_degradado", lambda db, tenant_id, diagnostico_id: True)
    orden: list[str] = []
    _espiar_fijar_contexto_tenant(monkeypatch, orden)
    db = _SesionEspia(orden)
    job = _JobFalso(estado="failed", intentos=plan_job.LIMITE_INTENTOS)

    resultado = plan_job.revisar_job_obsoleto(db, _TENANT_ID, job)

    assert resultado is False
    assert job.estado == "done"
    assert orden == ["commit", "fijar_contexto_tenant"]


def test_revisar_job_obsoleto_failed_con_reintento_disponible_refija_contexto_tenant(monkeypatch):
    orden: list[str] = []
    _espiar_fijar_contexto_tenant(monkeypatch, orden)
    db = _SesionEspia(orden)
    job = _JobFalso(estado="failed", intentos=0)

    resultado = plan_job.revisar_job_obsoleto(db, _TENANT_ID, job)

    assert resultado is True
    assert job.estado == "pending"
    assert orden == ["commit", "fijar_contexto_tenant"]


def test_revisar_job_obsoleto_running_obsoleto_con_limite_agotado_refija_contexto_tenant(monkeypatch):
    monkeypatch.setattr(plan_job, "_esta_obsoleto", lambda *args, **kwargs: True)
    monkeypatch.setattr(plan_job, "_persistir_plan_degradado", lambda db, tenant_id, diagnostico_id: False)
    orden: list[str] = []
    _espiar_fijar_contexto_tenant(monkeypatch, orden)
    db = _SesionEspia(orden)
    job = _JobFalso(estado="running", intentos=plan_job.LIMITE_INTENTOS - 1, updated_at=datetime.now(UTC))

    resultado = plan_job.revisar_job_obsoleto(db, _TENANT_ID, job)

    assert resultado is False
    assert job.intentos == plan_job.LIMITE_INTENTOS
    assert job.estado == "failed"
    assert orden == ["commit", "fijar_contexto_tenant"]


def test_revisar_job_obsoleto_running_obsoleto_con_reintento_disponible_refija_contexto_tenant(monkeypatch):
    monkeypatch.setattr(plan_job, "_esta_obsoleto", lambda *args, **kwargs: True)
    orden: list[str] = []
    _espiar_fijar_contexto_tenant(monkeypatch, orden)
    db = _SesionEspia(orden)
    job = _JobFalso(estado="running", intentos=0, updated_at=datetime.now(UTC))

    resultado = plan_job.revisar_job_obsoleto(db, _TENANT_ID, job)

    assert resultado is True
    assert job.intentos == 1
    assert job.estado == "pending"
    assert orden == ["commit", "fijar_contexto_tenant"]


# --- Creación automática de `AccionSeguimiento` al persistir un plan (F5/F6) -----
#
# Ambos caminos (degradado directo y camino feliz completo) deben crear exactamente
# una `AccionSeguimiento` por brecha del plan recién persistido, con los defaults
# documentados en `_crear_acciones_seguimiento`. Se ejercita con la `_SesionEspia`
# extendida de arriba -- sigue sin haber Postgres real en este repo.


def _tramite_de_prueba(tramite_id: UUID, tenant_id: UUID) -> Tramite:
    return Tramite(id=tramite_id, tenant_id=tenant_id, nombre="Trámite de prueba", estado="generando_plan")


def _diagnostico_de_prueba(diagnostico_id: UUID, tenant_id: UUID, tramite_id: UUID) -> DiagnosticoTramite:
    return DiagnosticoTramite(
        id=diagnostico_id, tenant_id=tenant_id, tramite_id=tramite_id, respuestas=RESPUESTAS_CON_BRECHAS
    )


def _tenant_de_prueba(tenant_id: UUID) -> Tenant:
    return Tenant(id=tenant_id, nombre="Gobierno de prueba", clave="demo", pais="mx")


def _verificar_acciones_creadas_una_por_brecha(db: _SesionEspia, tenant_id: UUID) -> None:
    planes = [obj for obj in db.agregados if isinstance(obj, PlanModernizacion)]
    acciones = [obj for obj in db.agregados if isinstance(obj, AccionSeguimiento)]
    assert len(planes) == 1
    brechas = planes[0].contenido["brechas"]
    assert len(brechas) > 0
    assert len(acciones) == len(brechas)

    descripciones_esperadas = {brecha["paso_administrativo"] for brecha in brechas}
    fecha_objetivo_esperada = datetime.now(UTC).date() + timedelta(days=90)
    for accion in acciones:
        assert accion.plan_modernizacion_id == planes[0].id
        assert accion.tenant_id == tenant_id
        assert accion.descripcion in descripciones_esperadas
        assert accion.responsable == "Por asignar"
        assert accion.fecha_objetivo == fecha_objetivo_esperada
        # `_crear_acciones_seguimiento` nunca fija `estado_semaforo` -- queda en
        # `None` acá porque el default Python-side de la columna
        # (backend/app/models/accion_seguimiento.py) solo se aplica al hacer INSERT
        # contra un motor real, y esta sesión de prueba no tiene uno (ver módulo).
        # Confirma la ausencia de asignación explícita, no el valor final en DB.
        assert accion.estado_semaforo is None


def test_persistir_plan_degradado_crea_una_accion_por_brecha():
    tenant_id, diagnostico_id, tramite_id = uuid4(), uuid4(), uuid4()
    db = _SesionEspia(
        [],
        diagnostico=_diagnostico_de_prueba(diagnostico_id, tenant_id, tramite_id),
        tenant=_tenant_de_prueba(tenant_id),
        tramite=_tramite_de_prueba(tramite_id, tenant_id),
        version_previa=None,
    )

    resultado = plan_job._persistir_plan_degradado(db, tenant_id, diagnostico_id)

    assert resultado is True
    _verificar_acciones_creadas_una_por_brecha(db, tenant_id)


def test_ejecutar_generacion_plan_camino_feliz_crea_una_accion_por_brecha(monkeypatch):
    tenant_id, diagnostico_id, tramite_id, job_id = uuid4(), uuid4(), uuid4(), uuid4()
    job = _JobFalso(estado="pending", intentos=0)
    db = _SesionEspia(
        [],
        job=job,
        diagnostico=_diagnostico_de_prueba(diagnostico_id, tenant_id, tramite_id),
        tenant=_tenant_de_prueba(tenant_id),
        tramite=_tramite_de_prueba(tramite_id, tenant_id),
        version_previa=None,
    )

    monkeypatch.setattr(plan_job, "abrir_sesion_tenant", lambda _tenant_id: db)
    monkeypatch.setattr(plan_job, "fijar_contexto_tenant", lambda _db, _tenant_id: None)
    # Fuerza el camino degradado -- ya cubierto por `_generar_contenido_y_modo` en
    # los tests de arriba; acá solo interesa la creación de `AccionSeguimiento`.
    monkeypatch.setattr(plan_job, "esta_disponible", lambda _ruta: False)

    plan_job.ejecutar_generacion_plan(job_id, tenant_id, diagnostico_id)

    assert job.estado == "done"
    _verificar_acciones_creadas_una_por_brecha(db, tenant_id)


# --- `revisar_job_obsoleto` contra Postgres real (RLS incluido) -----------------
#
# Hallazgo F7 de la auditoría final pre-Fase G: los 4 `db.commit()` de esta función
# solo se habían probado con `_SesionEspia` (arriba) -- eso verifica el ORDEN de las
# llamadas mockeadas, no que Postgres realmente vuelva a aceptar una consulta con
# RLS después del commit (mismo tipo de bug que el hotfix de
# `test_api_seguimiento.py::test_actualizar_accion_no_revienta_rls_tras_commit_contra_postgres_real`).
# Se salta limpio si no hay Postgres real alcanzable.


def _postgres_real_disponible() -> bool:
    """Mismo chequeo de dos pasos que `test_api_seguimiento.py`."""
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
def test_revisar_job_obsoleto_no_revienta_rls_tras_commit_contra_postgres_real():
    tenant_id = uuid4()
    db = abrir_sesion_tenant(tenant_id)
    try:
        db.add(Tenant(id=tenant_id, nombre="Tenant de prueba RLS", clave=f"prueba-rls-{tenant_id}", pais="mx"))
        db.flush()

        tramite = Tramite(tenant_id=tenant_id, nombre="Trámite de prueba RLS", estado="generando_plan")
        db.add(tramite)
        db.flush()

        diagnostico = DiagnosticoTramite(tenant_id=tenant_id, tramite_id=tramite.id, respuestas={})
        db.add(diagnostico)
        db.flush()

        # `updated_at` viejo a propósito -- más antiguo que el umbral de obsolescencia,
        # para que `revisar_job_obsoleto` tome la rama `running` (ver `_esta_obsoleto`).
        hace_rato = datetime.now(UTC) - timedelta(minutes=settings.job_umbral_obsoleto_minutos + 5)
        job = Job(
            tenant_id=tenant_id,
            tipo="generacion_plan",
            diagnostico_tramite_id=diagnostico.id,
            estado="running",
            intentos=0,
            updated_at=hace_rato,
        )
        db.add(job)
        db.commit()
        # mismo motivo que el commit de arriba en el setup de este mismo test --
        # también resetea el contexto, hay que refijarlo antes del siguiente `flush`.
        fijar_contexto_tenant(db, tenant_id)

        resultado = plan_job.revisar_job_obsoleto(db, tenant_id, job)

        assert resultado is True
        assert job.intentos == 1
        assert job.estado == "pending"

        # La consulta real que antes revienta: después de los `db.commit()` internos
        # de `revisar_job_obsoleto`, una consulta con RLS en la misma sesión debe
        # seguir funcionando -- exactamente el patrón de las tres rutas afectadas
        # (`GET /api/tramites`, `GET /api/tramites/{id}`, `GET /api/tramites/{id}/plan`).
        job_releido = db.get(Job, job.id)
        assert job_releido is not None
        assert job_releido.estado == "pending"

        tramites_del_tenant = db.execute(select(Tramite).where(Tramite.tenant_id == tenant_id)).scalars().all()
        assert len(tramites_del_tenant) == 1
        assert tramites_del_tenant[0].id == tramite.id
    finally:
        # limpieza explícita: hubo commits reales, un rollback no alcanza para
        # deshacerlos. El contexto de tenant ya quedó fijado por el último
        # `fijar_contexto_tenant` dentro de `revisar_job_obsoleto`.
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

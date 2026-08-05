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

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.engine.plantillas import generar_contenido_degradado
from app.ia import generador_plan, verificador
from app.jobs import plan_job

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


# --- (d) verificador no disponible (sin key para "economico") -> degradado, verificado=True ---


def test_verificador_no_disponible_cae_a_degradado(monkeypatch):
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: True)
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

    assert llamadas_auditoria == []  # el verificador nunca intentó auditar
    assert modo == "degradado"
    assert verificado is True
    assert contenido == generar_contenido_degradado(RESPUESTAS_CON_BRECHAS, "mx")


# --- (e) el verificador lanza una excepción (timeout/red) -> degradado, verificado=True ---


def test_verificador_lanza_excepcion_cae_a_degradado(monkeypatch):
    monkeypatch.setattr(plan_job, "esta_disponible", lambda ruta: True)
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


class _SesionEspia:
    """Sesión mínima que solo registra `commit` -- `revisar_job_obsoleto` no llama
    a ningún otro método de la sesión directamente cuando `_persistir_plan_degradado`
    está mockeado, como en los tests de este bloque."""

    def __init__(self, orden: list[str]) -> None:
        self._orden = orden

    def commit(self) -> None:
        self._orden.append("commit")


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

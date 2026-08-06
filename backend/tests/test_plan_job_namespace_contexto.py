"""Tests de `_namespace_efectivo` (backend/app/jobs/plan_job.py) y de su wiring
completo en `_persistir_plan_degradado` -- la fusión
`{**contexto_institucional_del_tenant, **respuestas_del_tramite}` que permite que
`autoridad_gobernanza_digital == false` se evalúe como brecha
(entregables/fase-2/variables-contexto-institucional.md, sección 3.1, punto 2).

Sin Postgres real: sesiones dobles en memoria, mismo criterio que
test_plan_job.py (`_SesionEspia`). A diferencia de aquella, esta sesión distingue
qué `select(...)` responde inspeccionando el texto SQL compilado -- necesario
porque, a diferencia de los tests ya existentes, acá coexisten dos consultas
`db.execute(...)` distintas (versión previa del plan y fila de
`contexto_institucional`) en el mismo flujo.
"""

from uuid import uuid4

from app.engine.plantillas import generar_contenido_degradado
from app.jobs import plan_job
from app.models import ContextoInstitucional, DiagnosticoTramite, PlanModernizacion, Tenant, Tramite

RESPUESTAS_NIVEL_MAXIMO = {
    "documentos_digitalizados": True,
    "motor_pagos": True,
    "firma_electronica_habilitada": True,
    "interoperabilidad": True,
    "proteccion_datos_incompleta": False,
    "mecanismo_identidad": "llave_mx",
}


class _ResultadoFalso:
    def __init__(self, valor: object) -> None:
        self._valor = valor

    def scalar_one_or_none(self) -> object:
        return self._valor


# --- (a) `_namespace_efectivo` pura, con una sesión mínima -----------------------


class _SesionSoloContexto:
    """Solo implementa `.execute()`, respondiendo siempre la misma fila (o `None`)
    de `contexto_institucional` -- suficiente para `_namespace_efectivo` a solas."""

    def __init__(self, contexto: ContextoInstitucional | None) -> None:
        self._contexto = contexto

    def execute(self, _stmt: object) -> _ResultadoFalso:
        return _ResultadoFalso(self._contexto)


def test_namespace_efectivo_sin_fila_de_contexto_devuelve_solo_respuestas():
    db = _SesionSoloContexto(None)
    respuestas = {"documentos_digitalizados": True}

    resultado = plan_job._namespace_efectivo(db, uuid4(), respuestas)

    assert resultado == respuestas


def test_namespace_efectivo_fusiona_contexto_y_respuestas_sin_colision():
    contexto = ContextoInstitucional(
        tenant_id=uuid4(),
        poblacion_total=5000,
        personal_total_gobierno=40,
        area_tic_existe=True,
        conectividad="intermitente",
        normativa_local_emitida=False,
        autoridad_gobernanza_digital=False,
    )
    db = _SesionSoloContexto(contexto)
    respuestas = {"documentos_digitalizados": True, "firma_electronica_habilitada": False}

    resultado = plan_job._namespace_efectivo(db, uuid4(), respuestas)

    assert resultado["documentos_digitalizados"] is True
    assert resultado["firma_electronica_habilitada"] is False
    assert resultado["autoridad_gobernanza_digital"] is False
    assert resultado["poblacion_total"] == 5000
    assert resultado["conectividad"] == "intermitente"


def test_namespace_efectivo_las_respuestas_del_tramite_ganan_si_hubiera_colision():
    # Ninguna de las 6 claves de `respuestas` colisiona hoy con las 7 de
    # contexto_institucional (confirmado en el diseño) -- este test fija el
    # contrato de prioridad de todos modos, por si alguna vez se agrega una clave
    # nueva que sí colisione.
    contexto = ContextoInstitucional(tenant_id=uuid4(), autoridad_gobernanza_digital=True)
    db = _SesionSoloContexto(contexto)
    respuestas = {"autoridad_gobernanza_digital": False}

    resultado = plan_job._namespace_efectivo(db, uuid4(), respuestas)

    assert resultado["autoridad_gobernanza_digital"] is False


# --- (b) la fusión efectivamente produce la brecha en modo degradado ------------


def test_fusion_produce_brecha_de_autoridad_gobernanza_digital_en_modo_degradado():
    contexto = ContextoInstitucional(tenant_id=uuid4(), autoridad_gobernanza_digital=False)
    db = _SesionSoloContexto(contexto)

    fusionado = plan_job._namespace_efectivo(db, uuid4(), RESPUESTAS_NIVEL_MAXIMO)
    contenido = generar_contenido_degradado(fusionado, "mx")

    variables = {b["variable"] for b in contenido["brechas"]}
    assert variables == {"autoridad_gobernanza_digital"}
    brecha = contenido["brechas"][0]
    assert brecha["categoria_catalogo"] == "gobernanza_institucional"
    # "gobernanza_institucional" no existe en el catálogo OSS (es una brecha
    # organizacional, no de adopción de software) -- degrada a None, nunca lanza.
    assert brecha["componente_recomendado"] is None


def test_sin_fila_de_contexto_no_produce_brecha_de_autoridad_ni_falla():
    db = _SesionSoloContexto(None)

    fusionado = plan_job._namespace_efectivo(db, uuid4(), RESPUESTAS_NIVEL_MAXIMO)
    contenido = generar_contenido_degradado(fusionado, "mx")

    assert contenido["brechas"] == []


# --- (c) wiring completo vía `_persistir_plan_degradado` ------------------------


class _SesionCompleta:
    """Extiende el patrón de `_SesionEspia` (test_plan_job.py) distinguiendo qué
    `select(...)` responde por el texto SQL compilado -- `_persistir_plan_degradado`
    hace dos `db.execute(select(...))` distintos en el mismo flujo (versión previa
    del plan, y ahora también la fila de `contexto_institucional`)."""

    def __init__(
        self,
        *,
        diagnostico: DiagnosticoTramite,
        tenant: Tenant,
        tramite: Tramite,
        contexto: ContextoInstitucional | None,
        version_previa: int | None = None,
    ) -> None:
        self.agregados: list[object] = []
        self._diagnostico = diagnostico
        self._tenant = tenant
        self._tramite = tramite
        self._contexto = contexto
        self._version_previa = version_previa

    def get(self, modelo: type, _id: object) -> object:
        if modelo is DiagnosticoTramite:
            return self._diagnostico
        if modelo is Tenant:
            return self._tenant
        if modelo is Tramite:
            return self._tramite
        raise AssertionError(f"get inesperado en la sesión de prueba: {modelo}")

    def execute(self, stmt: object) -> _ResultadoFalso:
        if "contexto_institucional" in str(stmt):
            return _ResultadoFalso(self._contexto)
        return _ResultadoFalso(self._version_previa)

    def add(self, obj: object) -> None:
        self.agregados.append(obj)

    def flush(self) -> None:
        pass


def test_persistir_plan_degradado_incluye_la_brecha_de_autoridad_cuando_hay_contexto():
    tenant_id, diagnostico_id, tramite_id = uuid4(), uuid4(), uuid4()
    diagnostico = DiagnosticoTramite(
        id=diagnostico_id, tenant_id=tenant_id, tramite_id=tramite_id, respuestas=RESPUESTAS_NIVEL_MAXIMO
    )
    tenant = Tenant(id=tenant_id, nombre="Gobierno de prueba", clave="demo", pais="mx")
    tramite = Tramite(id=tramite_id, tenant_id=tenant_id, nombre="Trámite de prueba", estado="generando_plan")
    contexto = ContextoInstitucional(tenant_id=tenant_id, autoridad_gobernanza_digital=False)

    db = _SesionCompleta(diagnostico=diagnostico, tenant=tenant, tramite=tramite, contexto=contexto)

    resultado = plan_job._persistir_plan_degradado(db, tenant_id, diagnostico_id)

    assert resultado is True
    planes = [obj for obj in db.agregados if isinstance(obj, PlanModernizacion)]
    assert len(planes) == 1
    variables = {b["variable"] for b in planes[0].contenido["brechas"]}
    assert variables == {"autoridad_gobernanza_digital"}


def test_persistir_plan_degradado_sin_fila_de_contexto_no_agrega_brecha_de_autoridad():
    tenant_id, diagnostico_id, tramite_id = uuid4(), uuid4(), uuid4()
    diagnostico = DiagnosticoTramite(
        id=diagnostico_id, tenant_id=tenant_id, tramite_id=tramite_id, respuestas=RESPUESTAS_NIVEL_MAXIMO
    )
    tenant = Tenant(id=tenant_id, nombre="Gobierno de prueba", clave="demo", pais="mx")
    tramite = Tramite(id=tramite_id, tenant_id=tenant_id, nombre="Trámite de prueba", estado="generando_plan")

    db = _SesionCompleta(diagnostico=diagnostico, tenant=tenant, tramite=tramite, contexto=None)

    resultado = plan_job._persistir_plan_degradado(db, tenant_id, diagnostico_id)

    assert resultado is True
    planes = [obj for obj in db.agregados if isinstance(obj, PlanModernizacion)]
    assert planes[0].contenido["brechas"] == []

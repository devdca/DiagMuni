"""Tests de app/aplicacion/sincronizacion_inegi.py -- sesión doble en memoria
(mismo criterio que test_api_gobierno_contexto.py), `cliente_inegi` mockeado
para no depender de red ni de un token real."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.adaptadores.inegi import cliente_inegi
from app.aplicacion import sincronizacion_inegi
from app.aplicacion.sincronizacion_inegi import SincronizacionInegiError, sincronizar_poblacion
from app.models import ContextoInstitucional, Tenant


class _ResultadoFalso:
    def __init__(self, valor: object) -> None:
        self._valor = valor

    def scalar_one_or_none(self) -> object:
        return self._valor


class _SesionFalsa:
    def __init__(self, fila: ContextoInstitucional | None = None) -> None:
        self.fila = fila
        self.agregados: list[ContextoInstitucional] = []

    def execute(self, _stmt: object) -> _ResultadoFalso:
        return _ResultadoFalso(self.fila)

    def add(self, obj: ContextoInstitucional) -> None:
        self.agregados.append(obj)


def _tenant(clave_geoestadistica: str | None = "09004") -> Tenant:
    return Tenant(
        id=uuid4(), nombre="Cuajimalpa", clave="cuajimalpa", pais="mx", clave_geoestadistica=clave_geoestadistica
    )


def test_sin_clave_geoestadistica_lanza_error_legible() -> None:
    with pytest.raises(SincronizacionInegiError, match="clave geoestadística"):
        sincronizar_poblacion(_SesionFalsa(), _tenant(clave_geoestadistica=None))


def test_sin_inegi_disponible_lanza_error_legible(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cliente_inegi, "esta_disponible", lambda: False)
    with pytest.raises(SincronizacionInegiError, match="no está configurada"):
        sincronizar_poblacion(_SesionFalsa(), _tenant())


def test_inegi_sin_dato_lanza_error_legible(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cliente_inegi, "esta_disponible", lambda: True)
    monkeypatch.setattr(cliente_inegi, "obtener_poblacion_total", lambda _clave: None)
    with pytest.raises(SincronizacionInegiError, match="Intenta de nuevo"):
        sincronizar_poblacion(_SesionFalsa(), _tenant())


def test_crea_fila_nueva_si_no_existia(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cliente_inegi, "esta_disponible", lambda: True)
    monkeypatch.setattr(cliente_inegi, "obtener_poblacion_total", lambda _clave: 217686)
    db = _SesionFalsa(fila=None)
    tenant = _tenant()

    fila = sincronizar_poblacion(db, tenant)

    assert fila in db.agregados
    assert fila.tenant_id == tenant.id
    assert fila.poblacion_total == 217686
    assert fila.poblacion_total_fuente == "inegi_api"
    assert fila.actualizado_en is not None


def test_actualiza_fila_existente_sin_pisar_otros_campos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cliente_inegi, "esta_disponible", lambda: True)
    monkeypatch.setattr(cliente_inegi, "obtener_poblacion_total", lambda _clave: 217686)
    tenant = _tenant()
    existente = ContextoInstitucional(
        tenant_id=tenant.id,
        poblacion_total=100,
        poblacion_total_fuente="manual",
        personal_total_gobierno=42,
        actualizado_en=datetime(2020, 1, 1, tzinfo=UTC),
    )
    db = _SesionFalsa(fila=existente)

    fila = sincronizar_poblacion(db, tenant)

    assert fila is existente
    assert db.agregados == []
    assert fila.poblacion_total == 217686
    assert fila.poblacion_total_fuente == "inegi_api"
    assert fila.personal_total_gobierno == 42


def test_resolver_tenant_delega_en_db_get() -> None:
    class _DbConGet:
        def __init__(self, tenant: Tenant) -> None:
            self._tenant = tenant

        def get(self, _modelo: object, tenant_id: object) -> Tenant | None:
            return self._tenant if tenant_id == self._tenant.id else None

    tenant = _tenant()
    assert sincronizacion_inegi.resolver_tenant(_DbConGet(tenant), tenant.id) is tenant

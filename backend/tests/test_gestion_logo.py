"""Tests puros de app/aplicacion/gestion_logo.py + app/adaptadores/almacenamiento/
logo_storage.py -- sin HTTP, sin Postgres (Tenant se construye en memoria, el
storage escribe a un directorio temporal vía monkeypatch de
settings.logo_storage_dir), mismo criterio que test_sincronizacion_inegi.py."""

from uuid import uuid4

import pytest

from app.adaptadores.almacenamiento import logo_storage
from app.aplicacion.gestion_logo import LogoInvalidoError, guardar_logo_tenant
from app.core.config import settings
from app.models import Tenant


@pytest.fixture(autouse=True)
def _storage_en_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "logo_storage_dir", str(tmp_path))


def _tenant_de_prueba() -> Tenant:
    return Tenant(id=uuid4(), nombre="Gobierno de prueba", clave=f"prueba-{uuid4()}", pais="mx")


def test_tipo_invalido_rechaza():
    tenant = _tenant_de_prueba()
    with pytest.raises(LogoInvalidoError, match="Tipo de archivo no permitido"):
        guardar_logo_tenant(tenant, b"contenido", "application/pdf")
    assert tenant.logo_content_type is None


def test_archivo_vacio_rechaza():
    tenant = _tenant_de_prueba()
    with pytest.raises(LogoInvalidoError, match="vacío"):
        guardar_logo_tenant(tenant, b"", "image/png")


def test_archivo_demasiado_grande_rechaza(monkeypatch):
    monkeypatch.setattr(settings, "logo_max_bytes", 10)
    tenant = _tenant_de_prueba()
    with pytest.raises(LogoInvalidoError, match="límite"):
        guardar_logo_tenant(tenant, b"x" * 11, "image/png")


def test_guardar_logo_actualiza_metadata_y_escribe_archivo():
    tenant = _tenant_de_prueba()
    guardar_logo_tenant(tenant, b"\x89PNG-falso", "image/png")

    assert tenant.logo_content_type == "image/png"
    assert tenant.logo_actualizado_en is not None
    assert logo_storage.leer_logo(tenant.id) == b"\x89PNG-falso"


def test_reemplazar_logo_ya_subido_sobrescribe_contenido_anterior():
    tenant = _tenant_de_prueba()
    guardar_logo_tenant(tenant, b"version-1", "image/png")
    primera_fecha = tenant.logo_actualizado_en

    guardar_logo_tenant(tenant, b"version-2-mas-larga", "image/jpeg")

    assert logo_storage.leer_logo(tenant.id) == b"version-2-mas-larga"
    assert tenant.logo_content_type == "image/jpeg"
    assert tenant.logo_actualizado_en >= primera_fecha


def test_storage_aisla_tenants_distintos():
    tenant_a = _tenant_de_prueba()
    tenant_b = _tenant_de_prueba()

    guardar_logo_tenant(tenant_a, b"logo-a", "image/png")

    assert logo_storage.leer_logo(tenant_a.id) == b"logo-a"
    assert logo_storage.leer_logo(tenant_b.id) is None


def test_leer_logo_sin_subir_devuelve_none():
    assert logo_storage.leer_logo(uuid4()) is None

"""Cubre app/core/cifrado.py: round-trip de cifrar/descifrar, y que un valor que
no descifra (clave rotada, dato corrupto) devuelva `None` en vez de lanzar --
quien llama (app/aplicacion/preferencia_modelo_ia.py::resolver_override) debe
poder tratar "no descifra" igual que "no hay credencial", nunca como una
excepción que tumbe una llamada de IA completa."""

from cryptography.fernet import Fernet

from app.core import cifrado
from app.core.config import Settings


def _cfg_con_clave(clave: str) -> Settings:
    return Settings(tenant_secret_key=clave)


def test_cifrar_y_descifrar_hace_roundtrip(monkeypatch):
    monkeypatch.setattr(cifrado, "settings", _cfg_con_clave(Fernet.generate_key().decode()))
    valor_cifrado = cifrado.cifrar("sk-anthropic-real-del-tenant")
    assert valor_cifrado != "sk-anthropic-real-del-tenant"
    assert cifrado.descifrar(valor_cifrado) == "sk-anthropic-real-del-tenant"


def test_descifrar_con_clave_distinta_devuelve_none_sin_lanzar(monkeypatch):
    monkeypatch.setattr(cifrado, "settings", _cfg_con_clave(Fernet.generate_key().decode()))
    valor_cifrado = cifrado.cifrar("sk-anthropic-real-del-tenant")

    monkeypatch.setattr(cifrado, "settings", _cfg_con_clave(Fernet.generate_key().decode()))
    assert cifrado.descifrar(valor_cifrado) is None


def test_descifrar_valor_corrupto_devuelve_none_sin_lanzar(monkeypatch):
    monkeypatch.setattr(cifrado, "settings", _cfg_con_clave(Fernet.generate_key().decode()))
    assert cifrado.descifrar("esto-no-es-un-token-fernet-valido") is None

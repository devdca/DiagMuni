"""Cifrado simétrico (Fernet) de credenciales de IA que cada tenant trae
consigo (BYOK) -- nunca en texto plano, nunca devueltas en claro por la API.

Clave separada de JWT_SECRET a propósito (radios de daño distintos si se
filtran). Fail-closed: un valor que no descifra devuelve `None`, nunca
lanza -- quien llama degrada a plantilla determinista."""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def cifrar(valor: str) -> str:
    return Fernet(settings.tenant_secret_key.encode()).encrypt(valor.encode()).decode()


def descifrar(valor_cifrado: str) -> str | None:
    try:
        return Fernet(settings.tenant_secret_key.encode()).decrypt(valor_cifrado.encode()).decode()
    except InvalidToken:
        return None

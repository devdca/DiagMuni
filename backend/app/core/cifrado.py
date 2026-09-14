"""Cifrado simétrico (Fernet) de credenciales de IA que cada tenant trae
consigo (BYOK, ver migración 0016 y app/models/tenant.py) -- nunca se guardan
en texto plano en `tenant`, nunca se devuelven en claro por la API una vez
guardadas (ver app/schemas/salud_ia.py: la respuesta solo expone un booleano
"¿hay algo guardado?", jamás el valor).

Clave de cifrado en `TENANT_SECRET_KEY` (app/core/config.py) -- separada de
`JWT_SECRET` a propósito, nunca reusar una clave entre propósitos distintos:
tienen radios de daño distintos si se filtran (una filtra sesiones, la otra
filtra API keys de proveedores de IA de terceros). Documentar backup/rotación
con el mismo criterio ya aplicado a JWT_SECRET -- rotarla invalida todas las
credenciales ya guardadas (cada tenant tendría que volver a pegar su key).

Fail-closed: un valor que no descifra (clave rotada, dato corrupto) devuelve
`None` en vez de lanzar -- quien llama ya sabe tratar "sin credencial" como
"degradar a plantilla determinista" (mismo patrón que `esta_disponible()` en
app/adaptadores/llm/config.py), nunca debe tumbar una llamada de IA completa
por un problema de descifrado."""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def cifrar(valor: str) -> str:
    return Fernet(settings.tenant_secret_key.encode()).encrypt(valor.encode()).decode()


def descifrar(valor_cifrado: str) -> str | None:
    try:
        return Fernet(settings.tenant_secret_key.encode()).decrypt(valor_cifrado.encode()).decode()
    except InvalidToken:
        return None

"""Cubre el guard de arranque de `Settings` para JWT_SECRET y TENANT_SECRET_KEY
(app/core/config.py): mismo principio que app/seed.py -- nunca romper dev/test,
pero abortar en producción si el operador dejó el secreto vacío o el valor de
ejemplo de .env.example. JWT_SECRET fue motivado por el hallazgo de Strix (un
secreto adivinable/público rompe autenticación y aislamiento entre gobiernos --
RLS -- por completo); TENANT_SECRET_KEY protege las credenciales de IA que cada
gobierno trae consigo (BYOK, app/core/cifrado.py)."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

# Clave Fernet válida (32 bytes en base64 urlsafe) para los casos "secreto real"
# de TENANT_SECRET_KEY -- cualquier clave con ese formato sirve para estos tests,
# no necesita ser la que use ningún despliegue real.
_TENANT_SECRET_KEY_REAL = "MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI="


@pytest.mark.parametrize(
    "secreto_placeholder", ["dev-secret-cambiar-en-produccion", "cambia-esto-por-un-secreto-real-y-largo", ""]
)
def test_produccion_aborta_con_secreto_placeholder_o_vacio(secreto_placeholder):
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(environment="production", jwt_secret=secreto_placeholder, tenant_secret_key=_TENANT_SECRET_KEY_REAL)


def test_produccion_acepta_secreto_real():
    settings = Settings(
        environment="production",
        jwt_secret="un-secreto-largo-y-aleatorio-real",
        tenant_secret_key=_TENANT_SECRET_KEY_REAL,
    )
    assert settings.jwt_secret == "un-secreto-largo-y-aleatorio-real"


def test_produccion_aborta_con_secreto_corto():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(environment="production", jwt_secret="abc123", tenant_secret_key=_TENANT_SECRET_KEY_REAL)


def test_development_no_aborta_con_secreto_corto():
    settings = Settings(environment="development", jwt_secret="abc123")
    assert settings.jwt_secret == "abc123"


@pytest.mark.parametrize(
    "secreto_placeholder", ["dev-secret-cambiar-en-produccion", "cambia-esto-por-un-secreto-real-y-largo", ""]
)
def test_development_no_aborta_con_secreto_placeholder(secreto_placeholder):
    """El default de desarrollo/tests debe seguir funcionando sin configuración
    adicional -- el guard es exclusivo de ENVIRONMENT=production."""
    settings = Settings(environment="development", jwt_secret=secreto_placeholder)
    assert settings.jwt_secret == secreto_placeholder


# --- TENANT_SECRET_KEY (BYOK, app/core/cifrado.py) -- mismo patrón que arriba ---


def test_produccion_aborta_con_tenant_secret_key_placeholder():
    # tenant_secret_key explícito -- sin esto, un .env real con una clave ya
    # generada (como la de este propio despliegue) se filtraría silenciosamente
    # a este test, igual que ya se documenta para llm_provider en test_ia_config.py.
    with pytest.raises(ValidationError, match="TENANT_SECRET_KEY"):
        Settings(
            environment="production",
            jwt_secret="un-secreto-largo-y-aleatorio-real",
            tenant_secret_key="ZGV2LXNlY3JldC1jYW1iaWFyLWVuLXByb2R1Y2Npb24=",
        )


def test_produccion_aborta_con_tenant_secret_key_vacio():
    with pytest.raises(ValidationError, match="TENANT_SECRET_KEY"):
        Settings(
            environment="production",
            jwt_secret="un-secreto-largo-y-aleatorio-real",
            tenant_secret_key="",
        )


def test_produccion_acepta_tenant_secret_key_real():
    settings = Settings(
        environment="production",
        jwt_secret="un-secreto-largo-y-aleatorio-real",
        tenant_secret_key=_TENANT_SECRET_KEY_REAL,
    )
    assert settings.tenant_secret_key == _TENANT_SECRET_KEY_REAL


def test_development_no_aborta_con_tenant_secret_key_placeholder():
    """El default de desarrollo/tests debe seguir funcionando sin configuración
    adicional -- el guard es exclusivo de ENVIRONMENT=production."""
    settings = Settings(environment="development")
    assert settings.tenant_secret_key

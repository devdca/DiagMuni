"""Cubre el guard de arranque de `Settings` para JWT_SECRET (app/core/config.py):
mismo principio que app/seed.py -- nunca romper dev/test, pero abortar en
producción si el operador dejó el secreto vacío o el valor de ejemplo de
.env.example. Motivado por el hallazgo de Strix: un JWT_SECRET adivinable/público
rompe autenticación y aislamiento entre gobiernos (RLS) por completo."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize(
    "secreto_placeholder", ["dev-secret-cambiar-en-produccion", "cambia-esto-por-un-secreto-real", ""]
)
def test_produccion_aborta_con_secreto_placeholder_o_vacio(secreto_placeholder):
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(environment="production", jwt_secret=secreto_placeholder)


def test_produccion_acepta_secreto_real():
    settings = Settings(environment="production", jwt_secret="un-secreto-largo-y-aleatorio-real")
    assert settings.jwt_secret == "un-secreto-largo-y-aleatorio-real"


@pytest.mark.parametrize(
    "secreto_placeholder", ["dev-secret-cambiar-en-produccion", "cambia-esto-por-un-secreto-real", ""]
)
def test_development_no_aborta_con_secreto_placeholder(secreto_placeholder):
    """El default de desarrollo/tests debe seguir funcionando sin configuración
    adicional -- el guard es exclusivo de ENVIRONMENT=production."""
    settings = Settings(environment="development", jwt_secret=secreto_placeholder)
    assert settings.jwt_secret == secreto_placeholder

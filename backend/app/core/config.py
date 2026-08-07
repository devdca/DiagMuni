from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Secretos de ejemplo/placeholder conocidos -- nunca válidos en producción (ver
# validador de abajo). Incluye el default de este módulo y el de .env.example.
_JWT_SECRETS_PLACEHOLDER = {
    "dev-secret-cambiar-en-produccion",
    "cambia-esto-por-un-secreto-real",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Guard para scripts destructivos/de datos ficticios (ver app/seed.py) — nunca "production" por defecto.
    environment: str = "development"

    # Rol de aplicación (sin privilegios de superusuario) — ver backend/db-init/01-app-role.sql
    # y la nota en .env.example sobre por qué esto es obligatorio para que RLS aplique de verdad.
    database_url: str = "postgresql+psycopg://diagmuni_app:diagmuni_app_password@localhost:5432/diagmuni"
    # Solo para Alembic (alembic/env.py) — rol superusuario, necesario para crear tablas/policies.
    migrations_database_url: str = "postgresql+psycopg://diagmuni:diagmuni@localhost:5432/diagmuni"
    jwt_secret: str = "dev-secret-cambiar-en-produccion"
    jwt_expire_hours: int = 8

    @model_validator(mode="after")
    def _jwt_secret_no_placeholder_en_produccion(self) -> "Settings":
        """Mismo principio que el guard de app/seed.py: nunca romper dev/test, pero
        abortar el arranque en producción si el operador dejó el secreto de ejemplo
        o vacío -- un secreto adivinable rompe autenticación y aislamiento RLS por
        completo (todo endpoint autenticado confía en el tenant_id/usuario_id del
        JWT, ver app/api/deps.py)."""
        if self.environment == "production" and (
            not self.jwt_secret or self.jwt_secret in _JWT_SECRETS_PLACEHOLDER
        ):
            raise ValueError(
                "JWT_SECRET no puede quedar vacío ni con el valor de ejemplo de "
                ".env.example cuando ENVIRONMENT=production. Genera uno real, p. ej.: "
                "python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return self

    # Capa de IA (docs/TRD.md) — opcional en fases A-D. Ausencia degrada a plantillas deterministas.
    llm_provider: str | None = None
    deepseek_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_api_base: str | None = None

    # Umbral del watchdog de jobs `running` obsoletos (docs/TRD.md, "Job asíncrono
    # — ciclo de vida"): sin actualización por más de este tiempo, se asume que el
    # proceso reinició a medio job y no se asume éxito silencioso.
    job_umbral_obsoleto_minutos: int = 15


settings = Settings()

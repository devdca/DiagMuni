from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Placeholders conocidos, nunca válidos en producción (ver validador abajo).
_JWT_SECRETS_PLACEHOLDER = {
    "dev-secret-cambiar-en-produccion",
    "cambia-esto-por-un-secreto-real-y-largo",
}

# RFC 7518 §3.2: mínimo recomendado para una clave HMAC-SHA256.
_JWT_SECRET_LONGITUD_MINIMA = 32

# Placeholder de TENANT_SECRET_KEY: clave Fernet válida pero reconociblemente
# insegura para dev/test. Nunca válida en producción.
_TENANT_SECRET_KEY_PLACEHOLDER = "ZGV2LXNlY3JldC1jYW1iaWFyLWVuLXByb2R1Y2Npb24="


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Guard para scripts destructivos/de datos ficticios (ver app/seed.py) — nunca "production" por defecto.
    environment: str = "development"

    # Rol de aplicación sin privilegios de superusuario -- obligatorio para que
    # RLS aplique de verdad (ver db-init/01-app-role.sql).
    database_url: str = "postgresql+psycopg://diagmuni_app:diagmuni_app_password@localhost:5432/diagmuni"
    # Solo para Alembic (alembic/env.py) — rol superusuario, necesario para crear tablas/policies.
    migrations_database_url: str = "postgresql+psycopg://diagmuni:diagmuni@localhost:5432/diagmuni"
    jwt_secret: str = "dev-secret-cambiar-en-produccion"
    jwt_expire_hours: int = 8

    # Cifra las credenciales de IA de cada tenant (BYOK) -- nunca reusar
    # JWT_SECRET. Debe ser una clave Fernet válida (`Fernet.generate_key()`).
    tenant_secret_key: str = _TENANT_SECRET_KEY_PLACEHOLDER

    @model_validator(mode="after")
    def _jwt_secret_no_placeholder_en_produccion(self) -> "Settings":
        """Nunca rompe dev/test, pero aborta el arranque en producción si el
        secreto quedó vacío o de ejemplo -- un secreto adivinable rompe
        autenticación y RLS por completo."""
        if self.environment == "production" and (
            not self.jwt_secret or self.jwt_secret in _JWT_SECRETS_PLACEHOLDER
        ):
            raise ValueError(
                "JWT_SECRET no puede quedar vacío ni con el valor de ejemplo de "
                ".env.example cuando ENVIRONMENT=production. Genera uno real, p. ej.: "
                "python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        if self.environment == "production" and len(self.jwt_secret) < _JWT_SECRET_LONGITUD_MINIMA:
            raise ValueError(
                f"JWT_SECRET debe tener al menos {_JWT_SECRET_LONGITUD_MINIMA} caracteres "
                "cuando ENVIRONMENT=production. Genera uno real, p. ej.: "
                "python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        if self.environment == "production" and (
            not self.tenant_secret_key or self.tenant_secret_key == _TENANT_SECRET_KEY_PLACEHOLDER
        ):
            raise ValueError(
                "TENANT_SECRET_KEY no puede quedar vacío ni con el valor de ejemplo de "
                ".env.example cuando ENVIRONMENT=production -- cifra las credenciales de "
                "IA que cada gobierno guarda (BYOK). Genera uno real, p. ej.: "
                'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        return self

    # Capa de IA (docs/TRD.md) — opcional en fases A-D. Ausencia degrada a plantillas deterministas.
    llm_provider: str | None = None
    deepseek_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_api_base: str | None = None

    # Umbral del watchdog de jobs `running` obsoletos: sin actualizar por más de
    # esto, se asume que el proceso reinició a medio job.
    job_umbral_obsoleto_minutos: int = 15

    # Token de INEGI (gratuito, inegi.org.mx/servicios/api_indicadores.html) para
    # prellenar `poblacion_total`. Su ausencia solo deshabilita la sincronización.
    inegi_api_token: str | None = None
    # Id de indicador de INEGI para "Población total" -- varía por censo/conteo,
    # confirmar contra el catálogo antes de cambiarlo.
    inegi_indicador_poblacion_total: str = "1002000001"

    # Logo del gobierno: archivo en disco, no blob en Postgres (ver
    # logo_storage.py). Tope acotado -- nginx necesita el mismo número (con
    # margen) en su propio client_max_body_size.
    logo_max_bytes: int = 3 * 1024 * 1024
    # Relativo al working directory del contenedor (/app) -- montado como
    # volumen `diagmuni_logos_data` para sobrevivir un rebuild.
    logo_storage_dir: str = "data/logos"

    # Captura de errores en producción (Sentry). Ausente: nunca se inicializa,
    # cero overhead.
    sentry_dsn: str | None = None


settings = Settings()

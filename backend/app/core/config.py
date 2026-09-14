from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Secretos de ejemplo/placeholder conocidos -- nunca válidos en producción (ver
# validador de abajo). Incluye el default de este módulo y el de .env.example.
_JWT_SECRETS_PLACEHOLDER = {
    "dev-secret-cambiar-en-produccion",
    "cambia-esto-por-un-secreto-real-y-largo",
}

# RFC 7518 §3.2: mínimo recomendado para una clave HMAC-SHA256.
_JWT_SECRET_LONGITUD_MINIMA = 32

# Placeholder de TENANT_SECRET_KEY (ver app/core/cifrado.py) -- base64 urlsafe de
# "dev-secret-cambiar-en-produccion" rellenado a 32 bytes, para que sea una clave
# Fernet válida en dev/test (Fernet exige exactamente ese formato) sin dejar de
# ser reconocible como insegura. Nunca válida en producción, mismo criterio que
# _JWT_SECRETS_PLACEHOLDER de arriba.
_TENANT_SECRET_KEY_PLACEHOLDER = "ZGV2LXNlY3JldC1jYW1iaWFyLWVuLXByb2R1Y2Npb24="


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

    # Cifra las credenciales de IA que cada tenant trae consigo (BYOK, ver
    # app/core/cifrado.py y Tenant.deepseek_api_key_cifrada/anthropic_api_key_cifrada)
    # -- nunca reusar JWT_SECRET, son propósitos distintos con distinto radio de
    # daño si se filtran. Debe ser una clave Fernet válida (32 bytes en base64
    # urlsafe, ej. `Fernet.generate_key()`).
    tenant_secret_key: str = _TENANT_SECRET_KEY_PLACEHOLDER

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

    # Umbral del watchdog de jobs `running` obsoletos (docs/TRD.md, "Job asíncrono
    # — ciclo de vida"): sin actualización por más de este tiempo, se asume que el
    # proceso reinició a medio job y no se asume éxito silencioso.
    job_umbral_obsoleto_minutos: int = 15

    # Integración con la API de Indicadores de INEGI (app/adaptadores/inegi/),
    # para prellenar `poblacion_total` en el Perfil del gobierno -- ver nota de
    # arquitectura "De Municipio a Tres Órdenes". Token gratuito de registro en
    # inegi.org.mx/servicios/api_indicadores.html -- no es un secreto de la
    # misma clase que JWT_SECRET/TENANT_SECRET_KEY (no protege datos propios de
    # DiagMuni), por eso no lleva validador anti-placeholder: su ausencia
    # simplemente deshabilita la sincronización (cierra de forma segura en cliente_inegi.py).
    inegi_api_token: str | None = None
    # Id de indicador del Banco de Indicadores para "Población total" -- variable
    # (no una constante en cliente_inegi.py) porque INEGI publica un id de
    # indicador distinto por censo/conteo; confirmar contra el catálogo de
    # indicadores antes de cambiarlo. Sin verificación en vivo contra la API real
    # todavía (sin token registrado al escribir esto) -- ver advertencia en
    # cliente_inegi.py.
    inegi_indicador_poblacion_total: str = "1002000001"


settings = Settings()

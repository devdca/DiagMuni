"""Carga de la configuración de la capa de IA (`litellm_config.yaml`) y detección
de disponibilidad de API key por ruta. Solo config y detección — ninguna llamada
real a un LLM vive en este módulo.

El YAML nunca se transcribe a código Python, igual que el catálogo de
`engine/reglas_loader.py` — cambiar de modelo/ruta es editar un archivo de texto.

Las API keys se leen de `app.core.config.Settings` (nunca de `os.environ`
directamente), el mismo mecanismo que usa el resto del backend. La convención de
pydantic-settings mapea cada variable de entorno a un atributo en minúsculas del
mismo nombre (`DEEPSEEK_API_KEY` -> `deepseek_api_key`), así que
`RutaLLM.env_var_api_key.lower()` localiza el atributo sin tabla de mapeo aparte.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from app.core.config import Settings
from app.core.config import settings as settings_global

CONFIG_PATH = Path(__file__).parent / "litellm_config.yaml"

_PREFIJO_ENV = "os.environ/"

_PROVEEDORES_RUTAS: dict[str, tuple[str, ...]] = {
    "anthropic": ("calidad", "calidad_respaldo", "local"),
    "local": ("local",),
    "deepseek": ("economico", "local"),
}


@dataclass(frozen=True)
class RutaLLM:
    """Configuración resuelta de una entrada de `model_list`. No contiene la API key
    en sí, solo el nombre de la variable de entorno — el valor se resuelve al
    consultar `esta_disponible()`/`api_key_de()`/`api_base_de()`, nunca al cargar el YAML."""

    model_name: str  # "economico" | "calidad" | "local"
    model: str  # ej. "deepseek/deepseek-chat"
    env_var_api_key: str | None  # ej. "DEEPSEEK_API_KEY"
    env_var_api_base: str | None  # ej. "OLLAMA_API_BASE"
    timeout_segundos: int = 30


def _extraer_nombre_env_ref(env_ref: str) -> str:
    """"os.environ/DEEPSEEK_API_KEY" -> "DEEPSEEK_API_KEY" (convención de LiteLLM
    para los campos `api_key` y `api_base` de `litellm_params`). Si el YAML no
    sigue esa convención, se conserva el valor tal cual -- no se oculta un error de
    configuración adivinando qué quiso decir el autor del YAML."""
    if env_ref.startswith(_PREFIJO_ENV):
        return env_ref[len(_PREFIJO_ENV) :]
    return env_ref


@lru_cache(maxsize=1)
def cargar_model_list() -> dict[str, RutaLLM]:
    """Lee `litellm_config.yaml` y arma un dict por `model_name` ("economico" /
    "calidad"). Cacheado igual que `engine/reglas_loader.cargar_catalogo()`: el
    archivo no cambia en caliente dentro de un mismo proceso corriendo; editarlo
    implica reiniciar el proceso, igual que con el catálogo de reglas."""
    with CONFIG_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    rutas: dict[str, RutaLLM] = {}
    for entrada in data["model_list"]:
        model_name = entrada["model_name"]
        params = entrada["litellm_params"]
        api_key_ref = params.get("api_key")
        api_base_ref = params.get("api_base")

        if bool(api_key_ref) == bool(api_base_ref):
            raise ValueError(
                f"Ruta LLM '{model_name}' en {CONFIG_PATH.name} debe declarar EXACTAMENTE "
                "uno de los campos 'api_key' o 'api_base'."
            )

        env_var_api_key = (
            _extraer_nombre_env_ref(api_key_ref) if api_key_ref is not None else None
        )
        env_var_api_base = (
            _extraer_nombre_env_ref(api_base_ref) if api_base_ref is not None else None
        )
        timeout_segundos = int(params.get("timeout_segundos", 30))

        rutas[model_name] = RutaLLM(
            model_name=model_name,
            model=params["model"],
            env_var_api_key=env_var_api_key,
            env_var_api_base=env_var_api_base,
            timeout_segundos=timeout_segundos,
        )
    return rutas


def obtener_ruta(nombre: str) -> RutaLLM:
    """`nombre`: "economico" | "calidad". Lanza `KeyError` si el YAML no define esa
    ruta — es un error de configuración real, no la ausencia de una API key, y debe
    fallar fuerte en vez de degradarse en silencio."""
    rutas = cargar_model_list()
    if nombre not in rutas:
        raise KeyError(
            f"Ruta LLM '{nombre}' no está definida en {CONFIG_PATH.name}. "
            f"Rutas disponibles: {sorted(rutas.keys())}."
        )
    return rutas[nombre]


def obtener_proveedor_llm(cfg: Settings | None = None) -> str | None:
    cfg = cfg if cfg is not None else settings_global
    provider = getattr(cfg, "llm_provider", None)
    if provider is not None:
        provider = provider.strip().lower()
        if provider:
            if provider not in _PROVEEDORES_RUTAS:
                raise ValueError(
                    f"LLM_PROVIDER '{provider}' no soportado. Use 'anthropic', 'deepseek' o 'local'."
                )
            return provider

    if esta_disponible("calidad", cfg=cfg):
        return "anthropic"
    if esta_disponible("economico", cfg=cfg):
        return "deepseek"
    if esta_disponible("local", cfg=cfg):
        return "local"
    return None


def obtener_rutas_generacion(cfg: Settings | None = None) -> list[str]:
    provider = obtener_proveedor_llm(cfg)
    if provider is None:
        return []
    return list(_PROVEEDORES_RUTAS[provider])


def api_key_de(ruta: RutaLLM, cfg: Settings | None = None) -> str | None:
    """Valor actual de la API key de `ruta`, leído desde `Settings`.

    Devuelve `None` tanto si la variable nunca se definió como si se definió vacía
    ("") -- ambos casos cuentan como "sin key" para quien llama.
    `cfg` es inyectable para tests; en producción se usa el singleton
    `app.core.config.settings`. Si la ruta declara `api_base` en lugar de `api_key`,
    devuelve `None`.
    """
    if ruta.env_var_api_key is None:
        return None
    cfg = cfg if cfg is not None else settings_global
    atributo = ruta.env_var_api_key.lower()
    valor = getattr(cfg, atributo, None)
    return valor if valor else None


def api_base_de(ruta: RutaLLM, cfg: Settings | None = None) -> str | None:
    """Valor actual de la API base de `ruta`, leído desde `Settings`.

    Devuelve `None` tanto si la variable nunca se definió como si se definió vacía
    ("") -- ambos casos cuentan como "sin base" para quien llama.
    `cfg` es inyectable para tests; en producción se usa el singleton
    `app.core.config.settings`. Si la ruta declara `api_key` en lugar de `api_base`,
    devuelve `None`.
    """
    if ruta.env_var_api_base is None:
        return None
    cfg = cfg if cfg is not None else settings_global
    atributo = ruta.env_var_api_base.lower()
    valor = getattr(cfg, atributo, None)
    return valor if valor else None


def esta_disponible(nombre_ruta: str, cfg: Settings | None = None) -> bool:
    """True si hay una API key o API base configurada (no vacía) para `nombre_ruta`.

    False sin excepción si falta o está vacía — quien llama usa este booleano para
    degradar a plantilla determinista en vez de intentar una llamada que fallaría."""
    ruta = obtener_ruta(nombre_ruta)
    if ruta.env_var_api_key is not None:
        return api_key_de(ruta, cfg=cfg) is not None
    if ruta.env_var_api_base is not None:
        return api_base_de(ruta, cfg=cfg) is not None
    return False

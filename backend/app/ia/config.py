"""Carga de la configuración de la capa de IA (docs/TRD.md, "Capa de IA —
configuración concreta") y detección de disponibilidad de API key por ruta.

Alcance de E1 (docs/plan-implementacion.md, fase E, pieza 1): SOLO config y
detección de disponibilidad. Ninguna llamada real a un LLM vive en este módulo --
eso queda para E2 (generador de plan, F3), E3 (verificador, F9) y E4 (asistente de
captura, F1), que se asignan después de que esta pieza esté auditada.

Nombre del módulo: se llama `config.py` (no `litellm_client.py`) porque, igual que
`app/core/config.py`, este archivo no llama a nada -- solo carga y expone
configuración. Un `litellm_client.py` (o similar) que sí invoque `litellm.completion`
es tarea de E2/E3/E4, no de E1.

Regla dura de docs/TRD.md ("Estructura de carpetas"): nada dentro de `engine/`
importa de `ia/`; la dependencia va en un solo sentido, `ia/` -> `engine/`. Este
módulo, a su vez, no importa nada de `app.engine` -- no lo necesita todavía (eso
llega con E2, que sí leerá el catálogo de `engine/reglas/` para construir el prompt).

Carga del YAML: igual que `app/engine/reglas_loader.py` con el catálogo brecha->
acción, `litellm_config.yaml` nunca se transcribe a código Python -- este módulo
solo lo lee en tiempo de ejecución, para que cambiar de modelo/ruta sea editar un
archivo de texto, no tocar código.

Fuente de las API keys: se apoya en `app.core.config.Settings` (Pydantic Settings),
el mismo mecanismo ya usado en el resto del backend -- no se lee `os.environ`
directamente aquí, para no crear un segundo mecanismo de configuración paralelo.
`Settings` ya expone `deepseek_api_key` y `anthropic_api_key` como `str | None`,
opcionales (fases A-D). La convención de pydantic-settings es mapear cada variable
de entorno a un atributo en minúsculas del mismo nombre (`DEEPSEEK_API_KEY` ->
`deepseek_api_key`), así que `RutaLLM.env_var_api_key.lower()` localiza el atributo
correspondiente sin necesidad de una tabla de mapeo adicional.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from app.core.config import Settings
from app.core.config import settings as settings_global

CONFIG_PATH = Path(__file__).parent / "litellm_config.yaml"

_PREFIJO_ENV = "os.environ/"


@dataclass(frozen=True)
class RutaLLM:
    """Configuración resuelta de una entrada de `model_list` (una ruta: "economico"
    o "calidad"). No contiene la API key en sí -- solo el *nombre* de la variable de
    entorno donde se espera encontrarla; el valor se resuelve al momento de
    consultar `esta_disponible()` / `api_key_de()`, nunca al cargar el YAML, para
    que un despliegue pueda montar el secreto después del arranque del proceso."""

    model_name: str  # "economico" | "calidad"
    model: str  # ej. "deepseek/deepseek-chat"
    env_var_api_key: str  # ej. "DEEPSEEK_API_KEY" (nombre de la variable, no su valor)


def _extraer_nombre_env_var(api_key_ref: str) -> str:
    """"os.environ/DEEPSEEK_API_KEY" -> "DEEPSEEK_API_KEY" (convención de LiteLLM
    para el campo `api_key` de `litellm_params`, ver docs/TRD.md). Si el YAML no
    sigue esa convención, se conserva el valor tal cual -- no se oculta un error de
    configuración adivinando qué quiso decir el autor del YAML."""
    if api_key_ref.startswith(_PREFIJO_ENV):
        return api_key_ref[len(_PREFIJO_ENV) :]
    return api_key_ref


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
        rutas[model_name] = RutaLLM(
            model_name=model_name,
            model=params["model"],
            env_var_api_key=_extraer_nombre_env_var(params["api_key"]),
        )
    return rutas


def obtener_ruta(nombre: str) -> RutaLLM:
    """nombre: "economico" | "calidad" (docs/TRD.md: F1 y F9 -> economico, F3 ->
    calidad). Lanza `KeyError` si el YAML no define esa ruta: eso es un error de
    configuración real (p. ej. quien llama pidió una ruta que no existe), no la
    ausencia de una API key en tiempo de ejecución -- debe fallar fuerte en
    desarrollo/CI, nunca degradarse en silencio como sí ocurre con la key ausente."""
    rutas = cargar_model_list()
    if nombre not in rutas:
        raise KeyError(
            f"Ruta LLM '{nombre}' no está definida en {CONFIG_PATH.name}. "
            f"Rutas disponibles: {sorted(rutas.keys())}."
        )
    return rutas[nombre]


def api_key_de(ruta: RutaLLM, cfg: Settings | None = None) -> str | None:
    """Valor actual de la API key de `ruta`, leído desde `Settings` (nunca desde
    `os.environ` directamente). Devuelve `None` tanto si la variable nunca se
    definió como si se definió vacía ("") -- ambos casos cuentan como "sin key" para
    quien llama. `cfg` es inyectable para tests; en producción se usa el singleton
    `app.core.config.settings`."""
    cfg = cfg if cfg is not None else settings_global
    atributo = ruta.env_var_api_key.lower()
    valor = getattr(cfg, atributo, None)
    return valor if valor else None


def esta_disponible(nombre_ruta: str, cfg: Settings | None = None) -> bool:
    """True si hay una API key configurada (no vacía) para `nombre_ruta`. False --
    sin excepción -- si falta o está vacía: quien llama (E2/E3/E4, más adelante) usa
    este booleano para decidir si degrada a plantilla determinista en vez de
    intentar una llamada que fallaría, conforme a docs/TRD.md ("Capa de IA"): "Si la
    API no responde... cae a plantilla determinista -- nunca un error visible al
    funcionario". El arranque de FastAPI (`app/main.py`) no depende de esta función
    ni de este módulo en absoluto, así que su resultado no puede romper el arranque
    en ningún escenario."""
    ruta = obtener_ruta(nombre_ruta)
    return api_key_de(ruta, cfg=cfg) is not None

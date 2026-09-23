"""Vigila GET <URL>/health y avisa a un webhook genérico (Slack/Discord/lo que
sea que reciba un POST JSON) tras M chequeos consecutivos fallidos -- evita
falsos positivos por un solo hiccup de red. El endpoint /health existe desde
el día uno (app/main.py); hasta ahora nada lo consultaba fuera de un chequeo
manual o el healthcheck interno de Docker Compose.

Corre FUERA de los contenedores (docs/runbook-despliegue.md, sección
"Vigilancia de /health") -- contra el puerto publicado de nginx, no dentro de
la red interna de Compose -- por eso vive en backend/scripts/ y no se copia a
ninguna imagen (backend/Dockerfile no lo incluye).

Uso:
  python scripts/vigilar_salud.py --url http://localhost:8090/health
  python scripts/vigilar_salud.py --url http://localhost:8090/health \
      --intervalo 30 --fallos-consecutivos 3 \
      --webhook https://hooks.slack.com/services/...

ALERTA_WEBHOOK_URL (variable de entorno, alternativa a --webhook): si ninguno
de los dos está presente, una caída se sigue registrando en el log -- el
script nunca falla por falta de configuración del webhook.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime

import httpx

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
logger = logging.getLogger("vigilar_salud")


def revisar_una_vez(url: str, timeout: float) -> tuple[bool, str]:
    """True si respondió 200 -- cualquier otra cosa (status distinto, timeout,
    conexión rechazada) cuenta como fallo, con el motivo como string."""
    try:
        respuesta = httpx.get(url, timeout=timeout)
    except httpx.HTTPError as error:
        return False, f"{type(error).__name__}: {error}"
    if respuesta.status_code != 200:
        return False, f"status_code={respuesta.status_code}"
    return True, ""


def enviar_alerta(webhook_url: str | None, mensaje: str, timeout: float) -> None:
    """`webhook_url` ausente: no hace nada -- el log ya se escribió antes de
    llamar a esta función. Un error al mandar el webhook (red caída, URL mal
    configurada) tampoco debe tronar el script: la caída real ya quedó
    registrada, que es el dato que importa conservar."""
    if not webhook_url:
        return
    try:
        httpx.post(webhook_url, json={"text": mensaje}, timeout=timeout)
    except httpx.HTTPError as error:
        logger.error("No se pudo mandar la alerta al webhook: %s: %s", type(error).__name__, error)


def vigilar(
    url: str,
    intervalo_segundos: float,
    fallos_consecutivos_para_alertar: int,
    webhook_url: str | None,
    timeout: float = 5.0,
    max_iteraciones: int | None = None,
) -> None:
    """`max_iteraciones=None` (default real): corre para siempre -- lo usa
    producción vía systemd timer/cron (docs/runbook-despliegue.md). Un valor
    finito es solo para tests, que no pueden depender de un loop infinito."""
    fallos_seguidos = 0
    alerta_ya_mandada = False
    iteraciones = 0

    while max_iteraciones is None or iteraciones < max_iteraciones:
        ok, motivo = revisar_una_vez(url, timeout)
        if ok:
            if alerta_ya_mandada:
                logger.info(
                    json.dumps(
                        {"evento": "salud_recuperada", "url": url, "timestamp": datetime.now(UTC).isoformat()},
                        ensure_ascii=False,
                    )
                )
            fallos_seguidos = 0
            alerta_ya_mandada = False
        else:
            fallos_seguidos += 1
            logger.warning(
                json.dumps(
                    {
                        "evento": "chequeo_salud_fallido",
                        "url": url,
                        "motivo": motivo,
                        "fallos_consecutivos": fallos_seguidos,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                    ensure_ascii=False,
                )
            )
            # Un solo aviso por racha, no uno por cada fallo posterior al umbral
            # -- `alerta_ya_mandada` se resetea arriba en cuanto vuelve a
            # responder, así que una caída sostenida no inunda el webhook.
            if fallos_seguidos >= fallos_consecutivos_para_alertar and not alerta_ya_mandada:
                enviar_alerta(
                    webhook_url,
                    f"{url} lleva {fallos_seguidos} chequeos seguidos fallando. Último motivo: {motivo}",
                    timeout,
                )
                alerta_ya_mandada = True

        iteraciones += 1
        if max_iteraciones is None or iteraciones < max_iteraciones:
            time.sleep(intervalo_segundos)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Vigila un endpoint /health y alerta a un webhook genérico tras fallos consecutivos."
    )
    parser.add_argument("--url", default="http://localhost:8090/health", help="URL a chequear (default: %(default)s).")
    parser.add_argument("--intervalo", type=float, default=30.0, help="Segundos entre chequeos (default: %(default)s).")
    parser.add_argument(
        "--fallos-consecutivos",
        type=int,
        default=3,
        dest="fallos_consecutivos",
        help="Fallos seguidos antes de alertar (default: %(default)s).",
    )
    parser.add_argument(
        "--webhook",
        default=None,
        help="URL del webhook. Si no se pasa, se usa ALERTA_WEBHOOK_URL; si tampoco existe, solo se loguea.",
    )
    parser.add_argument(
        "--timeout", type=float, default=5.0, help="Timeout por chequeo/alerta, en segundos (default: %(default)s)."
    )
    args = parser.parse_args()

    webhook_url = args.webhook or os.environ.get("ALERTA_WEBHOOK_URL") or None
    if not webhook_url:
        logger.info("ALERTA_WEBHOOK_URL no configurada -- las caídas solo se registrarán en este log.")

    logger.info(
        "Vigilando %s cada %ss (alerta tras %s fallos seguidos)...", args.url, args.intervalo, args.fallos_consecutivos
    )
    vigilar(args.url, args.intervalo, args.fallos_consecutivos, webhook_url, args.timeout)


if __name__ == "__main__":
    main()

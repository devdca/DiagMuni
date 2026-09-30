"""Inicialización de Sentry, separada de main.py para que el filtro de fallas
sea testeable sin recargar ese módulo. Los handlers que reportan explícito
(`pool_agotado`/`error_no_manejado`) siguen viviendo en main.py."""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.scrubber import EventScrubber

# 401/403/404 son respuestas normales de la API, no fallos -- solo 5xx cuenta
# como "falla" para las integraciones de abajo.
CODIGOS_HTTP_COMO_FALLA: frozenset[int] = frozenset(range(500, 600))


def inicializar_sentry(dsn: str | None) -> bool:
    """`dsn` ausente: no llama a `sentry_sdk.init`, cero overhead. Devuelve si
    se inicializó."""
    if not dsn:
        return False

    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            StarletteIntegration(failed_request_status_codes=CODIGOS_HTTP_COMO_FALLA),
            FastApiIntegration(failed_request_status_codes=CODIGOS_HTTP_COMO_FALLA),
        ],
        # Nunca cuerpo de request (login trae password, etc.) -- send_default_pii=False
        # + EventScrubber cubren encabezados y claves sensibles anidadas.
        max_request_body_size="never",
        send_default_pii=False,
        event_scrubber=EventScrubber(recursive=True),
    )
    return True

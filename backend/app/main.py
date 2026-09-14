import json
import logging
import sys
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

from app.adaptadores.http import (
    admin_salud_ia,
    admin_usuarios,
    asistente_captura,
    auth,
    diagnosticos,
    gobierno_contexto,
    gobiernos,
    historial,
    notificaciones,
    perfil_usuario,
    planes,
    seguimiento,
    tramites,
)

app = FastAPI(title="DiagMuni API")

_logger_errores = logging.getLogger("diagmuni.errores")
if not _logger_errores.handlers:  # evita duplicar la línea si el módulo se importa más de una vez
    _handler_errores = logging.StreamHandler(sys.stdout)
    _handler_errores.setFormatter(logging.Formatter("%(message)s"))
    _logger_errores.addHandler(_handler_errores)
    _logger_errores.setLevel(logging.INFO)


@app.exception_handler(SQLAlchemyTimeoutError)
def pool_agotado(request: Request, exc: SQLAlchemyTimeoutError) -> JSONResponse:
    """El pool de conexiones (app/db/session.py) se agotó bajo carga concurrente
    -- 503 con Retry-After en vez de un 500 genérico."""
    return JSONResponse(
        status_code=503,
        content={"detail": "Servicio no disponible, intenta de nuevo en unos segundos."},
        headers={"Retry-After": "5"},
    )


@app.exception_handler(Exception)
def error_no_manejado(request: Request, exc: Exception) -> JSONResponse:
    """Red de seguridad para cualquier excepción que no tenga un handler propio
    (el 503 de arriba, o los 4xx que ya resuelve FastAPI/Starlette). Sin esto,
    Starlette responde texto plano "Internal Server Error" -- inconsistente con
    el resto de la API, que siempre devuelve JSON -- y el traceback solo queda
    en la salida cruda que Uvicorn imprime a stderr, sin poder ubicarlo por
    ruta ni correlacionarlo con el resto de los logs de auditoría (`docker
    compose logs backend`). FastAPI corre con `debug` en su valor por defecto
    (False), así que ya no fugaba detalle al cliente en ningún caso -- este
    handler no tapa un hueco de seguridad, ordena el diagnóstico.

    Mismo criterio que app/core/audit_log.py: stdlib `logging` puro, una línea
    JSON a stdout, sin Sentry/OTel todavía (docs/stack-tecnologico.md)."""
    _logger_errores.error(
        json.dumps(
            {
                "evento": "error_no_manejado",
                "timestamp": datetime.now(UTC).isoformat(),
                "metodo": request.method,
                "ruta": request.url.path,
                "tipo_excepcion": type(exc).__name__,
            },
            ensure_ascii=False,
        ),
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Ocurrió un error interno. Intenta de nuevo más tarde."},
    )

app.include_router(auth.router)
app.include_router(gobiernos.router)
app.include_router(gobierno_contexto.router)
app.include_router(asistente_captura.router)
app.include_router(tramites.router)
app.include_router(diagnosticos.router)
app.include_router(planes.router)
app.include_router(seguimiento.router)
app.include_router(admin_usuarios.router)
app.include_router(admin_salud_ia.router)
app.include_router(perfil_usuario.router)
app.include_router(historial.router)
app.include_router(notificaciones.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

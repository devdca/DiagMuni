from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

from app.api import (
    asistente_captura,
    auth,
    diagnosticos,
    gobierno_contexto,
    gobiernos,
    planes,
    seguimiento,
    tramites,
)

app = FastAPI(title="DiagMuni API")


@app.exception_handler(SQLAlchemyTimeoutError)
def pool_agotado(request: Request, exc: SQLAlchemyTimeoutError) -> JSONResponse:
    """El pool de conexiones (app/db/session.py) se agotó bajo carga concurrente
    -- 503 con Retry-After en vez de un 500 genérico."""
    return JSONResponse(
        status_code=503,
        content={"detail": "Servicio no disponible, intenta de nuevo en unos segundos."},
        headers={"Retry-After": "5"},
    )

app.include_router(auth.router)
app.include_router(gobiernos.router)
app.include_router(gobierno_contexto.router)
app.include_router(asistente_captura.router)
app.include_router(tramites.router)
app.include_router(diagnosticos.router)
app.include_router(planes.router)
app.include_router(seguimiento.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

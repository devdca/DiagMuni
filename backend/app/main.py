from fastapi import FastAPI

from app.api import asistente_captura, auth, diagnosticos, gobiernos, planes, seguimiento, tramites

app = FastAPI(title="DiagMuni API")

app.include_router(auth.router)
app.include_router(gobiernos.router)
app.include_router(asistente_captura.router)
app.include_router(tramites.router)
app.include_router(diagnosticos.router)
app.include_router(planes.router)
app.include_router(seguimiento.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

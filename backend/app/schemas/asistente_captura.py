from pydantic import BaseModel


class ConsistenciaBooleanaRequest(BaseModel):
    """Texto de aclaración + valor ya marcado por el funcionario para una de las 5
    variables booleanas del catálogo (`docs/backend-schema.md`)."""

    texto_aclaracion: str
    valor_marcado: bool


class MecanismoIdentidadRequest(BaseModel):
    """Texto de "Otro, especifique" en la pregunta de mecanismo_identidad. Nunca
    incluye `pais`: se resuelve siempre en el servidor a partir de `Tenant`, nunca
    del cliente (ver `app/api/asistente_captura.py`)."""

    texto_aclaracion: str


class ClasificacionOut(BaseModel):
    categoria: str

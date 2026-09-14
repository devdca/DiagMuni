from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UsuarioResponse(BaseModel):
    id: UUID
    nombre: str
    email: str
    rol: str
    activo: bool
    ultimo_login_en: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CrearUsuarioRequest(BaseModel):
    nombre: str = Field(min_length=1)
    email: str
    # Default "funcionario" -- crear un admin_gobierno adicional es una elección
    # explícita de quien ya es admin, nunca el valor implícito de un formulario.
    rol: str = "funcionario"


class UsuarioConPasswordResponse(BaseModel):
    usuario: UsuarioResponse
    # Se muestra una sola vez en la respuesta de alta -- igual que la CLI
    # (docs/plan-implementacion-alta-gobierno.md), nunca se vuelve a poder consultar.
    password_temporal: str


class CambiarRolRequest(BaseModel):
    rol: str


class ResetearPasswordResponse(BaseModel):
    password_temporal: str


class CambiarPasswordPropiaRequest(BaseModel):
    password_actual: str
    password_nueva: str = Field(min_length=12)


class ActualizarPerfilRequest(BaseModel):
    nombre: str = Field(min_length=1)

from uuid import UUID

from pydantic import BaseModel


class GobiernoOut(BaseModel):
    # Solo lo necesario para completar el LoginRequest (tenant_id) y confirmar al
    # funcionario a qué gobierno está por entrar (nombre) -- nunca datos de usuario.
    tenant_id: UUID
    nombre: str

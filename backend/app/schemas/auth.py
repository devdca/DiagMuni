from uuid import UUID

from pydantic import BaseModel


class LoginRequest(BaseModel):
    # tenant_id explícito porque "email" solo es único por tenant (docs/backend-schema.md,
    # UniqueConstraint tenant_id+email) — corresponde a la "selección de gobierno" de
    # docs/ux-brief.md, pantalla 1.
    tenant_id: UUID
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

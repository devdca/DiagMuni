"""Panel de administración de usuarios (RBAC, migración 0011) -- gestión día a día
de los funcionarios de un gobierno por su propio `admin_gobierno`, sin depender de
que alguien técnico corra `app/bootstrap_tenant.py` a mano (docs/backend-schema.md,
"Riesgos abiertos" #1, ya resuelto). Toda la lógica real vive en
`app/aplicacion/gestion_usuarios.py`; este router solo traduce HTTP <-> casos de uso.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.adaptadores.http.deps import TokenData, get_db, requerir_admin
from app.aplicacion import gestion_usuarios
from app.schemas.usuario import (
    CambiarRolRequest,
    CrearUsuarioRequest,
    ResetearPasswordResponse,
    UsuarioConPasswordResponse,
    UsuarioResponse,
)

router = APIRouter(prefix="/api/admin/usuarios", tags=["admin-usuarios"])


@router.get("", response_model=list[UsuarioResponse])
def listar(
    token: Annotated[TokenData, Depends(requerir_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> list[UsuarioResponse]:
    return [UsuarioResponse.model_validate(u) for u in gestion_usuarios.listar_usuarios(db, token.tenant_id)]


@router.post("", response_model=UsuarioConPasswordResponse, status_code=status.HTTP_201_CREATED)
def crear(
    payload: CrearUsuarioRequest,
    token: Annotated[TokenData, Depends(requerir_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> UsuarioConPasswordResponse:
    try:
        resultado = gestion_usuarios.crear_usuario(
            db, tenant_id=token.tenant_id, email=payload.email, nombre=payload.nombre, rol=payload.rol
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if resultado is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Ya existe un usuario con ese correo en este gobierno."
        )

    usuario, password = resultado
    db.commit()
    return UsuarioConPasswordResponse(usuario=UsuarioResponse.model_validate(usuario), password_temporal=password)


@router.post("/{usuario_id}/desactivar", response_model=UsuarioResponse)
def desactivar(
    usuario_id: UUID,
    token: Annotated[TokenData, Depends(requerir_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> UsuarioResponse:
    try:
        usuario = gestion_usuarios.desactivar_usuario(db, tenant_id=token.tenant_id, usuario_id=usuario_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    db.commit()
    return UsuarioResponse.model_validate(usuario)


@router.post("/{usuario_id}/reactivar", response_model=UsuarioResponse)
def reactivar(
    usuario_id: UUID,
    token: Annotated[TokenData, Depends(requerir_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> UsuarioResponse:
    usuario = gestion_usuarios.reactivar_usuario(db, tenant_id=token.tenant_id, usuario_id=usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    db.commit()
    return UsuarioResponse.model_validate(usuario)


@router.patch("/{usuario_id}/rol", response_model=UsuarioResponse)
def cambiar_rol(
    usuario_id: UUID,
    payload: CambiarRolRequest,
    token: Annotated[TokenData, Depends(requerir_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> UsuarioResponse:
    try:
        usuario = gestion_usuarios.cambiar_rol(
            db, tenant_id=token.tenant_id, usuario_id=usuario_id, nuevo_rol=payload.rol
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    db.commit()
    return UsuarioResponse.model_validate(usuario)


@router.post("/{usuario_id}/resetear-password", response_model=ResetearPasswordResponse)
def resetear_password(
    usuario_id: UUID,
    token: Annotated[TokenData, Depends(requerir_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> ResetearPasswordResponse:
    password = gestion_usuarios.resetear_password_por_id(db, tenant_id=token.tenant_id, usuario_id=usuario_id)
    if password is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    db.commit()
    return ResetearPasswordResponse(password_temporal=password)

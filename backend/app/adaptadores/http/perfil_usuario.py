"""Autoservicio del propio usuario autenticado -- distinto de
`app/adaptadores/http/gobierno_contexto.py` ("Perfil del gobierno", el contexto
institucional del tenant) y de `app/adaptadores/http/admin_usuarios.py` (gestión
de OTROS usuarios por un admin_gobierno). Aquí cualquier rol autenticado gestiona
sus propios datos -- nunca requiere `requerir_admin`."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.adaptadores.http.deps import TokenData, get_current_token, get_db
from app.aplicacion import gestion_usuarios
from app.models import Usuario
from app.schemas.usuario import ActualizarPerfilRequest, CambiarPasswordPropiaRequest, UsuarioResponse

router = APIRouter(prefix="/api/usuarios/me", tags=["perfil-usuario"])


@router.get("", response_model=UsuarioResponse)
def obtener_mi_perfil(
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> UsuarioResponse:
    usuario = db.get(Usuario, token.usuario_id)
    if usuario is None:
        # No debería ocurrir: get_current_token ya resolvió este usuario_id hace un instante.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return UsuarioResponse.model_validate(usuario)


@router.patch("", response_model=UsuarioResponse)
def actualizar_mi_perfil(
    payload: ActualizarPerfilRequest,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> UsuarioResponse:
    try:
        usuario = gestion_usuarios.actualizar_nombre_propio(
            db, tenant_id=token.tenant_id, usuario_id=token.usuario_id, nombre=payload.nombre
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    db.commit()
    return UsuarioResponse.model_validate(usuario)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def cambiar_mi_password(
    payload: CambiarPasswordPropiaRequest,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    try:
        cambiado = gestion_usuarios.cambiar_password_propia(
            db,
            tenant_id=token.tenant_id,
            usuario_id=token.usuario_id,
            password_actual=payload.password_actual,
            password_nueva=payload.password_nueva,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not cambiado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    db.commit()

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TokenData, get_current_token, get_db
from app.models import Tramite
from app.schemas.tramite import TramiteCreate, TramiteOut

router = APIRouter(prefix="/api/tramites", tags=["tramites"])


@router.get("", response_model=list[TramiteOut])
def listar_tramites(db: Annotated[Session, Depends(get_db)]) -> list[Tramite]:
    return list(db.execute(select(Tramite)).scalars())


@router.post("", response_model=TramiteOut, status_code=status.HTTP_201_CREATED)
def crear_tramite(
    payload: TramiteCreate,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> Tramite:
    tramite = Tramite(tenant_id=token.tenant_id, nombre=payload.nombre, descripcion=payload.descripcion)
    db.add(tramite)
    db.commit()
    return tramite


@router.get("/{tramite_id}", response_model=TramiteOut)
def obtener_tramite(tramite_id: UUID, db: Annotated[Session, Depends(get_db)]) -> Tramite:
    tramite = db.get(Tramite, tramite_id)
    if tramite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trámite no encontrado")
    return tramite

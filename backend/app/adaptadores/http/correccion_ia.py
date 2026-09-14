from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.adaptadores.http.deps import TokenData, get_current_token, get_db, requerir_admin
from app.aplicacion.bitacora_correcciones import listar_correcciones, registrar_correccion
from app.schemas.correccion_ia import CorreccionIaOut, RegistrarCorreccionRequest

router = APIRouter(prefix="/api/correcciones-ia", tags=["correcciones-ia"])


@router.post("", response_model=CorreccionIaOut, status_code=status.HTTP_201_CREATED)
def registrar(
    payload: RegistrarCorreccionRequest,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> CorreccionIaOut:
    """Cualquier usuario autenticado puede registrar una corrección -- es la
    contraparte de que cualquier funcionario puede usar el asistente de
    captura (F1) que produce la salida que se está corrigiendo. Nunca falla
    "fuerte": el llamador (frontend) trata esto como telemetría de apoyo, no
    como parte del flujo principal de captura del diagnóstico."""
    fila = registrar_correccion(
        db,
        tenant_id=token.tenant_id,
        creado_por=token.usuario_id,
        tramite_id=payload.tramite_id,
        pieza=payload.pieza,
        entrada_llm=payload.entrada_llm,
        salida_llm=payload.salida_llm,
        correccion=payload.correccion,
        ruta_llm=payload.ruta_llm,
    )
    db.commit()
    db.refresh(fila)
    return CorreccionIaOut.model_validate(fila)


@router.get("", response_model=list[CorreccionIaOut])
def listar(
    _admin: Annotated[TokenData, Depends(requerir_admin)],
    db: Annotated[Session, Depends(get_db)],
    pieza: str | None = Query(default=None),
) -> list[CorreccionIaOut]:
    """Solo admin_gobierno -- panel de revisión de correcciones, no algo que un
    funcionario individual necesite ver del resto del gobierno."""
    filas = listar_correcciones(db, pieza=pieza)
    return [CorreccionIaOut.model_validate(fila) for fila in filas]

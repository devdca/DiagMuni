from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TokenData, get_current_token, get_db
from app.db.rls import fijar_contexto_tenant
from app.models import ContextoInstitucional
from app.schemas.gobierno_contexto import ContextoInstitucionalIn, ContextoInstitucionalOut

router = APIRouter(prefix="/api/gobierno/contexto", tags=["gobierno-contexto"])


def _shape_vacio(tenant_id: UUID) -> ContextoInstitucionalOut:
    """Shape sintetizado con los 8 campos de negocio en null -- usado cuando el
    tenant todavía no guardó ninguna fila (entregables/fase-2/
    variables-contexto-institucional.md, sección 5.2: este endpoint nunca
    responde 404)."""
    return ContextoInstitucionalOut(
        tenant_id=tenant_id,
        poblacion_total=None,
        personal_total_gobierno=None,
        presupuesto_tic_anual=None,
        area_tic_existe=None,
        conectividad=None,
        normativa_local_emitida=None,
        autoridad_gobernanza_digital=None,
        actualizado_en=None,
    )


def _obtener_fila(db: Session, tenant_id: UUID) -> ContextoInstitucional | None:
    return db.execute(
        select(ContextoInstitucional).where(ContextoInstitucional.tenant_id == tenant_id)
    ).scalar_one_or_none()


@router.get("", response_model=ContextoInstitucionalOut)
def obtener_contexto(
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> ContextoInstitucionalOut:
    fila = _obtener_fila(db, token.tenant_id)
    if fila is None:
        return _shape_vacio(token.tenant_id)
    return ContextoInstitucionalOut.model_validate(fila)


@router.put("", response_model=ContextoInstitucionalOut)
def guardar_contexto(
    payload: ContextoInstitucionalIn,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> ContextoInstitucionalOut:
    """Upsert parcial -- equivalente explícito a `INSERT ... ON CONFLICT (tenant_id)
    DO UPDATE` vía SELECT + INSERT/UPDATE (mismo criterio de "exclude_unset" que
    `AccionSeguimientoActualizar` en app/api/seguimiento.py). `created_at` solo se
    asigna en el primer INSERT (server_default de la columna); `actualizado_en` se
    reescribe en cada PUT exitoso."""
    fila = _obtener_fila(db, token.tenant_id)
    cambios = payload.model_dump(exclude_unset=True)

    if fila is None:
        fila = ContextoInstitucional(tenant_id=token.tenant_id, **cambios)
        db.add(fila)
    else:
        for campo, valor in cambios.items():
            setattr(fila, campo, valor)

    fila.actualizado_en = datetime.now(UTC)
    db.commit()
    # commit() termina la transacción y con ella el app.tenant_id local (ver
    # app/db/rls.py) -- hay que volver a fijarlo antes del refresh de abajo, que
    # dispara una consulta real con RLS.
    fijar_contexto_tenant(db, token.tenant_id)
    db.refresh(fila)
    return ContextoInstitucionalOut.model_validate(fila)

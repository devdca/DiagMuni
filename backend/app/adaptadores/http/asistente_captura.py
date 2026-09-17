from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.adaptadores.http.deps import TokenData, get_current_token, get_db
from app.adaptadores.llm.asistente_captura import clasificar_consistencia_booleana, clasificar_mecanismo_identidad
from app.aplicacion.preferencia_modelo_ia import resolver_override
from app.models.tenant import Tenant
from app.schemas.asistente_captura import ClasificacionOut, ConsistenciaBooleanaRequest, MecanismoIdentidadRequest

router = APIRouter(prefix="/api/asistente-captura", tags=["asistente-captura"])

# Llamada síncrona de vida corta -- ninguno de los dos endpoints persiste nada,
# solo devuelven la categoría sugerida; el frontend confirma antes de guardar.


@router.post("/consistencia-booleana", response_model=ClasificacionOut)
def clasificar_consistencia(
    payload: ConsistenciaBooleanaRequest,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> ClasificacionOut:
    """Clasifica si la aclaración de texto libre contradice el valor que el
    funcionario ya marcó en una de las 5 variables booleanas del catálogo."""
    tenant = db.get(Tenant, token.tenant_id)
    resultado = clasificar_consistencia_booleana(
        payload.texto_aclaracion, payload.valor_marcado, override=resolver_override(tenant)
    )
    return ClasificacionOut(categoria=resultado.categoria, ruta_llm=resultado.ruta_llm)


@router.post("/mecanismo-identidad", response_model=ClasificacionOut)
def clasificar_identidad(
    payload: MecanismoIdentidadRequest,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> ClasificacionOut:
    """Clasifica el texto de "Otro, especifique" en una de las categorías
    candidatas para el mecanismo de identidad. `pais` NUNCA se acepta del cliente:
    se resuelve siempre consultando `Tenant` con `token.tenant_id`, aunque el mismo
    servidor haya firmado el JWT que ya trae ese dato como claim informativo para
    el frontend (restricción de seguridad explícita del encargo)."""
    tenant = db.get(Tenant, token.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gobierno no encontrado")
    resultado = clasificar_mecanismo_identidad(
        payload.texto_aclaracion, tenant.pais, override=resolver_override(tenant)
    )
    return ClasificacionOut(categoria=resultado.categoria, ruta_llm=resultado.ruta_llm)

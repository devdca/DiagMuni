from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import TokenData, get_current_token, get_db
from app.ia.asistente_captura import clasificar_consistencia_booleana, clasificar_mecanismo_identidad
from app.models.tenant import Tenant
from app.schemas.asistente_captura import ClasificacionOut, ConsistenciaBooleanaRequest, MecanismoIdentidadRequest

router = APIRouter(prefix="/api/asistente-captura", tags=["asistente-captura"])

# Llamada síncrona de vida corta (mismo perfil de latencia que app/ia/verificador.py,
# TIMEOUT_SEGUNDOS = 15) -- no requiere una entrada nueva en el enum job.tipo
# (docs/backend-schema.md), ver entregables/fase-2/asistente-captura-f1.md sección 3.
# Ninguno de los dos endpoints persiste nada: solo devuelven la categoría sugerida,
# la confirmación humana en el frontend es lo único que produce un valor guardable
# (guardado real siempre vía PUT/POST de app/api/diagnosticos.py, sin tocar).


@router.post("/consistencia-booleana", response_model=ClasificacionOut)
def clasificar_consistencia(
    payload: ConsistenciaBooleanaRequest,
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> ClasificacionOut:
    """Clasifica si la aclaración de texto libre contradice el valor que el
    funcionario ya marcó en una de las 5 variables booleanas del catálogo."""
    categoria = clasificar_consistencia_booleana(payload.texto_aclaracion, payload.valor_marcado)
    return ClasificacionOut(categoria=categoria)


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
    categoria = clasificar_mecanismo_identidad(payload.texto_aclaracion, tenant.pais)
    return ClasificacionOut(categoria=categoria)

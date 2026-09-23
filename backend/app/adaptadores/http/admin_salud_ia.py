"""Panel de administración -- pestaña "Salud del sistema" (solo `admin_gobierno`):
qué proveedor de IA está activo, la propia credencial que el gobierno haya
configurado (BYOK, ver app/core/cifrado.py y app/aplicacion/preferencia_modelo_ia.py),
y qué generó recientemente -- sin ningún stack de observabilidad nuevo (docs/
TRD.md, "Observabilidad": "sin stack pesado... para el MVP"), todo derivado de
columnas que `tenant`, `plan_modernizacion` y `job` ya tienen.

Decisión de UX: no hay pestaña/página aparte para elegir proveedor -- vive en
esta misma pantalla, junto a las métricas, para que la tarjeta "Proveedor
activo" que ya se mostraba quede correcta al instante después de guardar."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adaptadores.http.deps import TokenData, get_db, requerir_admin
from app.aplicacion import preferencia_modelo_ia
from app.db.rls import fijar_contexto_tenant
from app.models import DiagnosticoTramite, Job, PlanModernizacion, Tenant, Tramite
from app.schemas.salud_ia import ActualizarProveedorLlmRequest, PlanRecienteOut, ResumenSaludIaOut

router = APIRouter(prefix="/api/admin/salud-ia", tags=["admin-salud-ia"])

_VENTANA_JOBS_FALLIDOS_HORAS = 24
_LIMITE_PLANES_RECIENTES = 10


def _planes_recientes(db: Session, limite: int) -> list[PlanRecienteOut]:
    filas = db.execute(
        select(PlanModernizacion, Tramite.nombre, Tramite.id)
        .join(DiagnosticoTramite, PlanModernizacion.diagnostico_tramite_id == DiagnosticoTramite.id)
        .join(Tramite, DiagnosticoTramite.tramite_id == Tramite.id)
        .order_by(PlanModernizacion.generado_en.desc())
        .limit(limite)
    ).all()
    return [
        PlanRecienteOut(
            tramite_id=tramite_id,
            tramite_nombre=tramite_nombre,
            version=plan.version,
            modo=plan.modo,
            verificado=plan.verificado,
            generado_en=plan.generado_en,
        )
        for plan, tramite_nombre, tramite_id in filas
    ]


def _armar_resumen(db: Session, tenant: Tenant | None) -> ResumenSaludIaOut:
    """Punto único de armado de la respuesta -- usado por `GET` y por `PATCH`
    (que devuelve el resumen ya actualizado, para que el frontend no tenga que
    hacer un segundo round-trip)."""
    planes_recientes = _planes_recientes(db, _LIMITE_PLANES_RECIENTES)
    ultimo_plan = planes_recientes[0] if planes_recientes else None

    desde = datetime.now(UTC) - timedelta(hours=_VENTANA_JOBS_FALLIDOS_HORAS)
    jobs_fallidos_24h = db.execute(
        select(func.count()).select_from(Job).where(Job.estado == "failed", Job.updated_at >= desde)
    ).scalar_one()

    return ResumenSaludIaOut(
        proveedor_activo=preferencia_modelo_ia.resolver_proveedor_activo(tenant),
        proveedor_preferido=tenant.proveedor_llm_preferido if tenant else None,
        proveedores_disponibles=sorted(preferencia_modelo_ia.proveedores_soportados()),
        deepseek_key_configurada=bool(tenant and tenant.deepseek_api_key_cifrada),
        anthropic_key_configurada=bool(tenant and tenant.anthropic_api_key_cifrada),
        ollama_api_base=tenant.ollama_api_base if tenant else None,
        ultimo_plan=ultimo_plan,
        jobs_fallidos_24h=jobs_fallidos_24h,
        planes_recientes=planes_recientes,
    )


@router.get("/resumen", response_model=ResumenSaludIaOut)
def obtener_resumen_salud_ia(
    token: Annotated[TokenData, Depends(requerir_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> ResumenSaludIaOut:
    tenant = db.get(Tenant, token.tenant_id)
    return _armar_resumen(db, tenant)


@router.patch("/proveedor", response_model=ResumenSaludIaOut)
def actualizar_proveedor(
    payload: ActualizarProveedorLlmRequest,
    token: Annotated[TokenData, Depends(requerir_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> ResumenSaludIaOut:
    """BYOK: el propio gobierno guarda su proveedor preferido y/o su credencial
    (cifrada antes de guardarse, ver app/core/cifrado.py) -- nunca se devuelve en
    claro, ni siquiera en esta misma respuesta."""
    try:
        tenant = preferencia_modelo_ia.actualizar_preferencia(
            db, tenant_id=token.tenant_id, cambios=payload.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gobierno no encontrado")
    db.commit()
    # commit() resetea app.tenant_id -- _armar_resumen consulta tablas con RLS, refijar antes.
    fijar_contexto_tenant(db, token.tenant_id)
    return _armar_resumen(db, tenant)

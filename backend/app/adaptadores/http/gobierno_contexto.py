from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adaptadores.http.deps import TokenData, get_current_token, get_db
from app.aplicacion.sincronizacion_inegi import SincronizacionInegiError, resolver_tenant, sincronizar_poblacion
from app.db.rls import fijar_contexto_tenant
from app.models import ContextoInstitucional
from app.schemas.gobierno_contexto import ContextoInstitucionalIn, ContextoInstitucionalOut

router = APIRouter(prefix="/api/gobierno/contexto", tags=["gobierno-contexto"])


def _shape_vacio(tenant_id: UUID) -> ContextoInstitucionalOut:
    """Shape sintetizado con todos los campos de negocio en null -- usado cuando
    el tenant todavía no guardó ninguna fila (entregables/fase-2/
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
        agenda_simplificacion_publicada=None,
        portal_datos_abiertos_existe=None,
        linea_atencion_ciudadana_centralizada=None,
        capacitacion_personal_tic_anual=None,
        protocolo_ciberseguridad_existe=None,
        presupuesto_total_anual=None,
        numero_tramites_totales=None,
        ingresos_propios_porcentaje=None,
        numero_oficinas_atencion=None,
        enlace_notificado_formalmente=None,
        convenio_colaboracion_estado=None,
        personal_area_ti=None,
        infraestructura_firma_electronica=None,
        porcentaje_tramites_en_linea=None,
        porcentaje_tramites_en_linea_no_se_mide=False,
        portal_tramites_tipo=None,
        pagos_electronicos_generalizados=None,
        mecanismo_identidad_estandar=None,
        interoperabilidad_entre_areas=None,
        inventario_sistemas_existe=None,
        politica_gobierno_datos_existe=None,
        respaldos_periodicos_existen=None,
        incidente_ciberseguridad_24meses=None,
        certificacion_seguridad_externa=None,
        rotacion_personal_ti=None,
        dependencia_outsourcing_ti=None,
        mide_tiempos_resolucion=None,
        mide_satisfaccion_ciudadana=None,
        tablero_indicadores_existe=None,
        fondos_digitalizacion_recibidos=None,
        fondos_digitalizacion_detalle=None,
        porcentaje_poblacion_acceso_internet=None,
        porcentaje_poblacion_acceso_internet_no_se_tiene_dato=False,
        accesibilidad_sistemas_discapacidad=None,
        catalogo_tramites_propio_existe=None,
        poblacion_total_fuente=None,
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
    reescribe en cada PUT exitoso.

    Migración 0019: un PUT que toca `poblacion_total` es siempre captura manual
    del funcionario (nunca llega por aquí un valor de INEGI, ver
    POST /sincronizar-poblacion-inegi abajo) -- se marca `poblacion_total_fuente`
    en consecuencia, pisando cualquier "inegi_api" previo. Si el funcionario
    borra el campo (lo manda en null), la fuente también se limpia -- no hay
    nada que atribuir a un valor vacío."""
    fila = _obtener_fila(db, token.tenant_id)
    cambios = payload.model_dump(exclude_unset=True)
    if "poblacion_total" in cambios:
        cambios["poblacion_total_fuente"] = "manual" if cambios["poblacion_total"] is not None else None

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


@router.post("/sincronizar-poblacion-inegi", response_model=ContextoInstitucionalOut)
def sincronizar_poblacion_inegi(
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> ContextoInstitucionalOut:
    """Trae `poblacion_total` desde la API de Indicadores de INEGI (ver
    app/aplicacion/sincronizacion_inegi.py) y la guarda con
    `poblacion_total_fuente="inegi_api"`. Acción explícita del funcionario
    (botón "Sincronizar con INEGI" en el Perfil del gobierno), no automática --
    un dato oficial nuevo nunca debe aparecer sin que alguien lo haya pedido."""
    tenant = resolver_tenant(db, token.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Gobierno no encontrado.")

    try:
        fila = sincronizar_poblacion(db, tenant)
    except SincronizacionInegiError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    db.commit()
    fijar_contexto_tenant(db, token.tenant_id)
    db.refresh(fila)
    return ContextoInstitucionalOut.model_validate(fila)

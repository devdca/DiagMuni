"""Subida y descarga del logo de un gobierno -- GET/PUT sobre un único recurso
por tenant, mismo patrón de "un registro por tenant" que gobierno_contexto.py.

`nombre_gobierno` sí viaja como claim del JWT (app/core/security.py) porque casi
nunca cambia. Un logo es un archivo que el gobierno puede reemplazar cuando
quiera -- un token ya emitido no se refresca solo, así que se consulta aparte en
cada carga en vez de meterlo en el token.

Ningún endpoint recibe un tenant_id por URL: `get_current_token` resuelve el
tenant contra la base de datos y nunca confía en el claim crudo (ver
app/adaptadores/http/deps.py), así que no hay manera de pedir/reemplazar el
logo de otro gobierno más que forjando un token válido de ese otro gobierno --
el mismo perímetro de aislamiento que protege el resto de la API.

La subida además exige `admin_gobierno` (requerir_admin): un funcionario raso
puede VER el logo (aparece en su propio encabezado/Panel resumen) pero no
reemplazarlo -- mismo criterio de superficie de administración que
admin_usuarios.py/admin_salud_ia.py. GET no lo exige a propósito: cualquier
funcionario autenticado de ese tenant necesita poder cargarlo para su propia UI."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.adaptadores.almacenamiento import logo_storage
from app.adaptadores.http.deps import TokenData, get_current_token, get_db, requerir_admin
from app.aplicacion.gestion_logo import LogoInvalidoError, guardar_logo_tenant
from app.core.config import settings
from app.models import Tenant

router = APIRouter(prefix="/api/gobierno/logo", tags=["gobierno-logo"])

_TAMANO_LOTE_LECTURA = 64 * 1024


async def _leer_con_limite(archivo: UploadFile, limite_bytes: int) -> bytes:
    """Lee `archivo` en bloques en vez de `await archivo.read()` a secas -- corta
    apenas se supera el límite configurado, sin bufferear en memoria un archivo
    arbitrariamente grande. nginx ya aplica su propio `client_max_body_size` en
    esta ruta (nginx/nginx.conf), pero el backend no debe confiar en que siempre
    hay un proxy delante (ej. en dev sin Docker, acceso directo al puerto 8000)."""
    partes: list[bytes] = []
    total = 0
    while True:
        trozo = await archivo.read(_TAMANO_LOTE_LECTURA)
        if not trozo:
            break
        total += len(trozo)
        if total > limite_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"El archivo supera el límite de {limite_bytes / (1024 * 1024):.0f} MB.",
            )
        partes.append(trozo)
    return b"".join(partes)


@router.put("", status_code=204)
async def subir_logo(
    archivo: UploadFile,
    token: Annotated[TokenData, Depends(requerir_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Reemplaza el logo actual del tenant si ya había uno (idempotente: subir
    dos veces dos archivos válidos deja vigente el segundo, sin dejar rastro del
    primero en disco -- ver logo_storage.guardar_logo)."""
    tenant = db.get(Tenant, token.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Gobierno no encontrado.")

    contenido = await _leer_con_limite(archivo, settings.logo_max_bytes)
    try:
        guardar_logo_tenant(tenant, contenido, archivo.content_type)
    except LogoInvalidoError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    db.commit()
    return Response(status_code=204)


@router.get("")
def obtener_logo(
    token: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    tenant = db.get(Tenant, token.tenant_id)
    if tenant is None or tenant.logo_content_type is None:
        raise HTTPException(status_code=404, detail="Este gobierno no tiene un logo configurado.")

    contenido = logo_storage.leer_logo(token.tenant_id)
    if contenido is None:
        # Metadata sin archivo en disco (no debería pasar) -- 404, mismo resultado
        # visible que "nunca subió uno".
        raise HTTPException(status_code=404, detail="Este gobierno no tiene un logo configurado.")

    return Response(content=contenido, media_type=tenant.logo_content_type)

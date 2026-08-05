from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

EstadoSemaforo = Literal["completado", "en_progreso", "atrasado"]


class AccionSeguimientoOut(BaseModel):
    id: UUID
    plan_modernizacion_id: UUID
    descripcion: str
    responsable: str
    fecha_objetivo: date
    estado_semaforo: EstadoSemaforo
    actualizado_en: datetime
    # Resueltos server-side vía join AccionSeguimiento -> PlanModernizacion ->
    # DiagnosticoTramite -> Tramite (sin relationship ORM entre esas tablas, ver
    # backend/app/api/planes.py) -- el panel de seguimiento mezcla acciones de
    # varios trámites y necesita saber a cuál pertenece cada fila para navegar.
    tramite_id: UUID
    tramite_nombre: str

    model_config = {"from_attributes": True}


class AccionSeguimientoActualizar(BaseModel):
    """Edición inline de un campo a la vez en la tabla del panel de seguimiento
    (docs/app-flow.md, paso 5) -- los 3 campos son opcionales porque el funcionario
    edita uno solo por vez, nunca los tres juntos en una misma petición."""

    responsable: str | None = None
    fecha_objetivo: date | None = None
    estado_semaforo: EstadoSemaforo | None = None

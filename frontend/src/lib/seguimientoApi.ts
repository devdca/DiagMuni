import { apiFetch } from "./httpClient";
import type { EstadoSemaforo } from "./semaforo";

// Forma exacta de backend/app/schemas/accion_seguimiento.py::AccionSeguimientoOut
// (extendido con tramite_id/tramite_nombre -- ver backend/app/api/seguimiento.py,
// _construir_accion_out): la tabla del panel de seguimiento mezcla acciones de
// varios trámites y necesita saber a cuál pertenece cada fila para navegar a
// /tramites/:tramiteId/plan al hacer clic.
export interface AccionSeguimientoResponse {
  id: string;
  plan_modernizacion_id: string;
  descripcion: string;
  responsable: string;
  fecha_objetivo: string;
  estado_semaforo: EstadoSemaforo;
  actualizado_en: string;
  tramite_id: string;
  tramite_nombre: string;
}

// Los 3 campos editables inline (docs/app-flow.md, "el cambio de estado del
// semáforo es una acción simple en la misma tabla") -- siempre uno a la vez,
// por eso todos son opcionales acá; `descripcion`/`plan_modernizacion_id`/
// `tenant_id` nunca se envían (backend/app/schemas/accion_seguimiento.py::
// AccionSeguimientoActualizar no los acepta).
export interface ActualizarAccionSeguimientoPayload {
  responsable?: string;
  fecha_objetivo?: string;
  estado_semaforo?: EstadoSemaforo;
}

export function listarAccionesSeguimiento(): Promise<AccionSeguimientoResponse[]> {
  return apiFetch<AccionSeguimientoResponse[]>("/api/seguimiento");
}

export function actualizarAccionSeguimiento(
  accionId: string,
  payload: ActualizarAccionSeguimientoPayload,
): Promise<AccionSeguimientoResponse> {
  return apiFetch<AccionSeguimientoResponse>(`/api/seguimiento/${accionId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

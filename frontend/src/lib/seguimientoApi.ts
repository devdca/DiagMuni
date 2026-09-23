import { apiFetch } from "./httpClient";
import type { EstadoSemaforo } from "./semaforo";

// Incluye tramite_id/tramite_nombre: la tabla mezcla acciones de varios trámites
// y necesita saber a cuál pertenece cada fila para navegar al hacer clic.
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

// Los 3 campos editables inline, siempre uno a la vez -- todos opcionales.
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

export interface NotaSeguimientoResponse {
  id: string;
  accion_seguimiento_id: string;
  usuario_id: string;
  usuario_nombre: string;
  texto: string;
  creado_en: string;
}

export function listarNotasDeAccion(accionId: string): Promise<NotaSeguimientoResponse[]> {
  return apiFetch<NotaSeguimientoResponse[]>(`/api/seguimiento/${accionId}/notas`);
}

export function agregarNotaAAccion(accionId: string, texto: string): Promise<NotaSeguimientoResponse> {
  return apiFetch<NotaSeguimientoResponse>(`/api/seguimiento/${accionId}/notas`, {
    method: "POST",
    body: JSON.stringify({ texto }),
  });
}

import { apiFetch } from "./httpClient";

// Espejo de backend/app/schemas/historial.py::EventoHistorialOut (migración
// 0012) -- bitácora persistida por trámite, pestaña "Historial" del plan.
export interface EventoHistorialResponse {
  id: string;
  tipo: string;
  descripcion: string;
  usuario_id: string | null;
  metadatos: Record<string, unknown> | null;
  creado_en: string;
}

export function obtenerHistorial(tramiteId: string): Promise<EventoHistorialResponse[]> {
  return apiFetch<EventoHistorialResponse[]>(`/api/tramites/${tramiteId}/historial`);
}

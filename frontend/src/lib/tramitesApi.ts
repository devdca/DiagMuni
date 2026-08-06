import { apiFetch } from "./httpClient";

// Mismos valores de app/models/tramite.py::ESTADOS_TRAMITE.
export type EstadoTramite = "sin_iniciar" | "en_progreso" | "diagnosticado" | "generando_plan" | "plan_listo";

export interface TramiteResponse {
  id: string;
  nombre: string;
  descripcion: string;
  estado: EstadoTramite;
  created_at: string;
  updated_at: string;
  indice_madurez: number | null;
  completado_en: string | null;
}

// Forma de GET /api/tramites (backend/app/schemas/tramite.py::PanelResumenOut):
// la lista de trámites ya trae su índice individual, más el agregado del panel
// resumen ya calculado en el backend (backend/app/engine/madurez.py,
// calcular_indice_global) -- el frontend nunca reimplementa esa fórmula.
export interface PanelResumenResponse {
  tramites: TramiteResponse[];
  indice_global: number | null;
  fecha_ultimo_diagnostico: string | null;
}

export function obtenerPanelResumen(): Promise<PanelResumenResponse> {
  return apiFetch<PanelResumenResponse>("/api/tramites");
}

export function obtenerTramite(tramiteId: string): Promise<TramiteResponse> {
  return apiFetch<TramiteResponse>(`/api/tramites/${tramiteId}`);
}

// Forma de POST /api/tramites (backend/app/schemas/tramite.py::TramiteCreate).
export interface TramiteCrearPayload {
  nombre: string;
  descripcion?: string;
}

export function crearTramite(payload: TramiteCrearPayload): Promise<TramiteResponse> {
  return apiFetch<TramiteResponse>("/api/tramites", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

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
  archivado_en: string | null;
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

// `incluirArchivados`: refleja el query param `archivados` de GET /api/tramites
// (backend/app/api/tramites.py) -- por defecto solo activos; con `true` devuelve
// EXCLUSIVAMENTE los archivados (nunca ambos mezclados, ver diseño del endpoint).
export function obtenerPanelResumen(incluirArchivados = false): Promise<PanelResumenResponse> {
  return apiFetch<PanelResumenResponse>(`/api/tramites${incluirArchivados ? "?archivados=true" : ""}`);
}

export function eliminarTramite(tramiteId: string): Promise<void> {
  return apiFetch<void>(`/api/tramites/${tramiteId}`, { method: "DELETE" });
}

export function archivarTramite(tramiteId: string): Promise<TramiteResponse> {
  return apiFetch<TramiteResponse>(`/api/tramites/${tramiteId}/archivar`, { method: "POST" });
}

export function desarchivarTramite(tramiteId: string): Promise<TramiteResponse> {
  return apiFetch<TramiteResponse>(`/api/tramites/${tramiteId}/desarchivar`, { method: "POST" });
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

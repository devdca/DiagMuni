import { apiFetch } from "./httpClient";

// Mismos valores de app/models/tramite.py::ESTADOS_TRAMITE.
export type EstadoTramite = "sin_iniciar" | "en_progreso" | "diagnosticado" | "generando_plan" | "plan_listo";

export interface TramiteResponse {
  id: string;
  nombre: string;
  descripcion: string;
  estado: EstadoTramite;
  tipo: string;
  created_at: string;
  updated_at: string;
  indice_madurez: number | null;
  completado_en: string | null;
  archivado_en: string | null;
}

// Decide qué preguntas muestra Diagnostico.tsx para cada trámite.
export interface VariableAdicionalResponse {
  variable: string;
  pregunta: string;
  ayuda: string;
}

export interface TipoTramiteResponse {
  nombre: string;
  etiqueta: string;
  variables_excluidas: string[];
  variables_adicionales: VariableAdicionalResponse[];
}

export function obtenerTiposTramite(): Promise<TipoTramiteResponse[]> {
  return apiFetch<TipoTramiteResponse[]>("/api/tramites/tipos");
}

// El índice global ya viene calculado del backend -- el frontend nunca reimplementa la fórmula.
export interface PanelResumenResponse {
  tramites: TramiteResponse[];
  indice_global: number | null;
  fecha_ultimo_diagnostico: string | null;
}

// `incluirArchivados=true` devuelve EXCLUSIVAMENTE archivados, nunca mezclados.
export function obtenerPanelResumen(incluirArchivados = false): Promise<PanelResumenResponse> {
  return apiFetch<PanelResumenResponse>(`/api/tramites${incluirArchivados ? "?archivados=true" : ""}`);
}

// Un punto real por cada envío/corrección de diagnóstico, nunca simulado, más
// antiguo primero. `nivel_N_conteo`: distribución real por nivel en ese instante.
export interface PuntoIndiceGlobalResponse {
  indice_global: number;
  nivel_0_conteo: number;
  nivel_1_conteo: number;
  nivel_2_conteo: number;
  nivel_3_conteo: number;
  nivel_4_conteo: number;
  creado_en: string;
}

export function obtenerHistorialIndiceGlobal(): Promise<PuntoIndiceGlobalResponse[]> {
  return apiFetch<PuntoIndiceGlobalResponse[]>("/api/tramites/indice-global/historial");
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

export interface TramiteCrearPayload {
  nombre: string;
  descripcion?: string;
  tipo?: string;
}

export function crearTramite(payload: TramiteCrearPayload): Promise<TramiteResponse> {
  return apiFetch<TramiteResponse>("/api/tramites", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

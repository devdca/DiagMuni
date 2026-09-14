import { apiFetch } from "./httpClient";

// Espejo de backend/app/schemas/salud_ia.py -- panel de administración, pestaña
// "Salud del sistema" (solo admin_gobierno). Todo derivado de columnas que ya
// existen (plan_modernizacion, job, tenant), sin tabla ni métrica nueva.
export interface PlanRecienteResponse {
  tramite_id: string;
  tramite_nombre: string;
  version: number;
  modo: "llm" | "degradado";
  verificado: boolean;
  generado_en: string;
}

// BYOK (bring your own key, ver app/core/cifrado.py): cada gobierno trae y paga
// su propia credencial de IA -- en un despliegue real el operador no deja
// ninguna key propia configurada.
export type ProveedorLlm = "anthropic" | "deepseek" | "local";

export interface ResumenSaludIaResponse {
  proveedor_activo: ProveedorLlm | null;
  proveedor_preferido: ProveedorLlm | null;
  proveedores_disponibles: ProveedorLlm[];
  // Las credenciales cifradas NUNCA viajan en claro -- solo estos booleanos.
  deepseek_key_configurada: boolean;
  anthropic_key_configurada: boolean;
  ollama_api_base: string | null;
  ultimo_plan: PlanRecienteResponse | null;
  jobs_fallidos_24h: number;
  planes_recientes: PlanRecienteResponse[];
}

export interface ActualizarProveedorLlmPayload {
  proveedor?: ProveedorLlm | null;
  deepseek_api_key?: string;
  anthropic_api_key?: string;
  ollama_api_base?: string;
}

export function obtenerResumenSaludIa(): Promise<ResumenSaludIaResponse> {
  return apiFetch<ResumenSaludIaResponse>("/api/admin/salud-ia/resumen");
}

export function actualizarProveedorLlm(
  cambios: ActualizarProveedorLlmPayload,
): Promise<ResumenSaludIaResponse> {
  return apiFetch<ResumenSaludIaResponse>("/api/admin/salud-ia/proveedor", {
    method: "PATCH",
    body: JSON.stringify(cambios),
  });
}

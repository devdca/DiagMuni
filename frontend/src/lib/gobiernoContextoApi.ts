import { apiFetch } from "./httpClient";

// Forma exacta de GET/PUT /api/gobierno/contexto (backend/app/schemas/
// gobierno_contexto.py) -- las 7 variables de contexto y capacidad institucional
// (entregables/fase-2/variables-contexto-institucional.md), capturadas una sola
// vez por gobierno (tenant), nunca por trámite.
export type Conectividad = "estable" | "intermitente" | "sin_conexion";

export interface ContextoInstitucionalResponse {
  tenant_id: string;
  poblacion_total: number | null;
  personal_total_gobierno: number | null;
  presupuesto_tic_anual: string | null;
  area_tic_existe: boolean | null;
  conectividad: Conectividad | null;
  normativa_local_emitida: boolean | null;
  autoridad_gobernanza_digital: boolean | null;
  actualizado_en: string | null;
}

// Upsert parcial -- cada campo es opcional, un PUT puede tocar uno solo sin
// reenviar los demás (backend/app/api/gobierno_contexto.py::guardar_contexto).
// `presupuesto_tic_anual` viaja como `number` en el request (Pydantic acepta
// número o string para un campo `Decimal`) aunque la respuesta lo devuelva como
// `string` (representación exacta de un `Decimal`, sin redondeo de punto flotante).
export interface ContextoInstitucionalPayload {
  poblacion_total?: number;
  personal_total_gobierno?: number;
  presupuesto_tic_anual?: number;
  area_tic_existe?: boolean;
  conectividad?: Conectividad;
  normativa_local_emitida?: boolean;
  autoridad_gobernanza_digital?: boolean;
}

// Nunca 404 -- si el tenant todavía no guardó ningún campo, el backend sintetiza
// el shape completo con los 8 campos de negocio en null.
export function obtenerContextoInstitucional(): Promise<ContextoInstitucionalResponse> {
  return apiFetch<ContextoInstitucionalResponse>("/api/gobierno/contexto");
}

export function guardarContextoInstitucional(
  payload: ContextoInstitucionalPayload,
): Promise<ContextoInstitucionalResponse> {
  return apiFetch<ContextoInstitucionalResponse>("/api/gobierno/contexto", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

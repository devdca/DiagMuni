import { ApiError, apiFetch } from "./httpClient";

// Variables del cuestionario (ver backend/app/engine/reglas/*.yaml) -- no
// incluye contexto/capacidad institucional, eso vive en gobiernoContextoApi.
export interface RespuestasDiagnostico {
  documentos_digitalizados?: boolean;
  motor_pagos?: boolean;
  firma_electronica_habilitada?: boolean;
  interoperabilidad?: boolean;
  proteccion_datos_incompleta?: boolean;
  tramite_completo_en_linea?: boolean;
  registrado_portal_ciudadano_unico?: boolean;
  notificaciones_automaticas?: boolean;
  disponible_movil?: boolean;
  plazo_respuesta_publicado?: boolean;
  silencio_administrativo_definido?: boolean;
  mecanismo_quejas_digital?: boolean;
  fundamento_juridico_vigente?: boolean;
  costo_publicado_en_linea?: boolean;
  revisado_ultimos_12_meses?: boolean;
  personal_capacitado_tramite_digital?: boolean;
  medicion_tiempo_satisfaccion?: boolean;
  version_accesible?: boolean;
  atencion_lengua_indigena?: boolean;
  requisitos_publicados_claramente?: boolean;
  // Informativo, no genera brecha -- opcional, no bloquea el envío.
  volumen_demanda_anual?: string;
  tramite_concurrente?: boolean;
  tramite_concurrente_detalle?: string;
  // "otro" es un estado transitorio de la UI -- nunca se envía al backend.
  mecanismo_identidad?: string;
  // Evidencia de apoyo opcional -- nunca reemplaza la respuesta cerrada.
  aclaraciones?: Record<string, string>;
  // Variables propias del tipo de trámite -- nombre dinámico.
  [variableAdicional: string]: boolean | string | Record<string, string> | undefined;
}

export interface DiagnosticoResponse {
  id: string;
  tramite_id: string;
  respuestas: RespuestasDiagnostico;
  indice_madurez: number | null;
  version_motor: string | null;
  completado_en: string | null;
}

// `null` (404) es normal la primera vez que se abre el cuestionario, no un error.
export async function obtenerDiagnostico(tramiteId: string): Promise<DiagnosticoResponse | null> {
  try {
    return await apiFetch<DiagnosticoResponse>(`/api/tramites/${tramiteId}/diagnostico`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

// "Guardar y continuar después" -- respuestas parciales, no calcula índice.
export function guardarDiagnostico(
  tramiteId: string,
  respuestas: RespuestasDiagnostico,
): Promise<DiagnosticoResponse> {
  return apiFetch<DiagnosticoResponse>(`/api/tramites/${tramiteId}/diagnostico`, {
    method: "PUT",
    body: JSON.stringify({ respuestas }),
  });
}

// Envío completo -- calcula el índice y dispara el job de plan.
export function enviarDiagnostico(
  tramiteId: string,
  respuestas: RespuestasDiagnostico,
): Promise<DiagnosticoResponse> {
  return apiFetch<DiagnosticoResponse>(`/api/tramites/${tramiteId}/diagnostico/enviar`, {
    method: "POST",
    body: JSON.stringify({ respuestas }),
  });
}

// Simulador "qué pasa si" -- corre el motor sobre el formulario sin guardar nada.
// `indice_actual` es el ya persistido (`null` si nunca se envió).
export interface SimulacionResponse {
  indice_actual: number | null;
  indice_proyectado: number;
}

export function simularDiagnostico(
  tramiteId: string,
  respuestas: RespuestasDiagnostico,
): Promise<SimulacionResponse> {
  return apiFetch<SimulacionResponse>(`/api/tramites/${tramiteId}/diagnostico/simular`, {
    method: "POST",
    body: JSON.stringify({ respuestas }),
  });
}

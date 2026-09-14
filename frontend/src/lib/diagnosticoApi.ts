import { ApiError, apiFetch } from "./httpClient";

// Las 6 variables reales del cuestionario (docs/backend-schema.md,
// backend/app/engine/reglas/*.yaml) -- ninguna variable de contexto/capacidad
// institucional adicional, esas son alcance aspiracional de producto, no de esta
// pantalla (docs/PRD.md línea 30, fuera de alcance de F3).
export interface RespuestasDiagnostico {
  documentos_digitalizados?: boolean;
  motor_pagos?: boolean;
  firma_electronica_habilitada?: boolean;
  interoperabilidad?: boolean;
  proteccion_datos_incompleta?: boolean;
  // 14 variables adicionales del cuestionario base (fase de expansión del
  // documento de especificación) -- mismo tratamiento transversal que
  // proteccion_datos_incompleta arriba, ver backend/app/engine/reglas/*.yaml.
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
  // Contexto adicional puramente informativo (no genera brecha, ver
  // backend/app/ia/estimacion_recursos.py) -- opcional, no bloquea el envío.
  volumen_demanda_anual?: string;
  tramite_concurrente?: boolean;
  tramite_concurrente_detalle?: string;
  // Solo uno de los 4 valores canónicos ("llave_mx" | "id_uruguay" | "propio" |
  // "ninguno") -- "otro" es un estado transitorio de la interfaz, nunca se envía
  // al backend (entregables/fase-2/asistente-captura-f1.md, sección 3).
  mecanismo_identidad?: string;
  // Evidencia de apoyo opcional, ligada a la variable que la motivó -- nunca
  // reemplaza por sí sola la respuesta cerrada.
  aclaraciones?: Record<string, string>;
  // Variables propias del tipo de trámite (backend/app/engine/tipos_tramite.yaml)
  // -- nombre dinámico, no forma parte del catálogo fijo de 6 de arriba.
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

// `null` si el diagnóstico todavía no se ha iniciado (404 del backend) -- estado
// normal la primera vez que el funcionario abre el cuestionario, nunca un error
// que deba mostrarse.
export async function obtenerDiagnostico(tramiteId: string): Promise<DiagnosticoResponse | null> {
  try {
    return await apiFetch<DiagnosticoResponse>(`/api/tramites/${tramiteId}/diagnostico`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

// "Guardar y continuar después" -- respuestas parciales, no calcula índice ni
// dispara el plan (backend/app/api/diagnosticos.py::guardar_diagnostico).
export function guardarDiagnostico(
  tramiteId: string,
  respuestas: RespuestasDiagnostico,
): Promise<DiagnosticoResponse> {
  return apiFetch<DiagnosticoResponse>(`/api/tramites/${tramiteId}/diagnostico`, {
    method: "PUT",
    body: JSON.stringify({ respuestas }),
  });
}

// Envío completo -- calcula el índice (F2, síncrono) y dispara automáticamente el
// job de plan (backend/app/api/diagnosticos.py::enviar_diagnostico).
export function enviarDiagnostico(
  tramiteId: string,
  respuestas: RespuestasDiagnostico,
): Promise<DiagnosticoResponse> {
  return apiFetch<DiagnosticoResponse>(`/api/tramites/${tramiteId}/diagnostico/enviar`, {
    method: "POST",
    body: JSON.stringify({ respuestas }),
  });
}

// Simulador "qué pasa si" -- corre el motor determinista sobre `respuestas` tal
// como están en el formulario, SIN guardar nada (backend/app/adaptadores/http/
// diagnosticos.py::simular_diagnostico). `indice_actual` es el ya persistido
// (`null` si el diagnóstico nunca se envió).
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

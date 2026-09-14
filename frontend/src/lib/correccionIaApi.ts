import { apiFetch } from "./httpClient";

// Cliente de POST /api/correcciones-ia (backend/app/adaptadores/http/
// correccion_ia.py) -- bitácora de correcciones humanas sobre salidas de la
// capa de IA (nunca "reentrenar el modelo": esto alimenta few-shot/evaluación
// futuros, ver app/aplicacion/bitacora_correcciones.py). Telemetría de apoyo:
// un fallo al registrar una corrección nunca debe bloquear el flujo principal
// de captura del diagnóstico -- quien llama decide si ignora el error.

export interface RegistrarCorreccionPayload {
  pieza: string;
  entrada_llm: string;
  salida_llm: string;
  correccion: string;
  tramite_id?: string;
  ruta_llm?: string;
}

export function registrarCorreccionIa(payload: RegistrarCorreccionPayload): Promise<unknown> {
  return apiFetch("/api/correcciones-ia", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

import { apiFetch } from "./httpClient";

// Cliente de los dos endpoints de asistencia de captura F1
// (backend/app/api/asistente_captura.py) -- nunca persisten nada, solo devuelven
// una categoría sugerida que el funcionario debe confirmar o descartar en la UI.

export interface ClasificacionResponse {
  categoria: string;
}

export function clasificarConsistenciaBooleana(
  textoAclaracion: string,
  valorMarcado: boolean,
): Promise<ClasificacionResponse> {
  return apiFetch<ClasificacionResponse>("/api/asistente-captura/consistencia-booleana", {
    method: "POST",
    body: JSON.stringify({ texto_aclaracion: textoAclaracion, valor_marcado: valorMarcado }),
  });
}

// Nunca se envía `pais`: el backend lo resuelve siempre desde `Tenant`
// (backend/app/api/asistente_captura.py::clasificar_identidad).
export function clasificarMecanismoIdentidad(textoAclaracion: string): Promise<ClasificacionResponse> {
  return apiFetch<ClasificacionResponse>("/api/asistente-captura/mecanismo-identidad", {
    method: "POST",
    body: JSON.stringify({ texto_aclaracion: textoAclaracion }),
  });
}

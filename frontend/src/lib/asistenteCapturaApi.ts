import { apiFetch } from "./httpClient";

// Nunca persisten nada -- solo devuelven una categoría sugerida que el
// funcionario debe confirmar o descartar en la UI.
export interface ClasificacionResponse {
  categoria: string;
  ruta_llm?: string | null;
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

// Nunca se envía `pais`: el backend lo resuelve siempre desde `Tenant`.
export function clasificarMecanismoIdentidad(textoAclaracion: string): Promise<ClasificacionResponse> {
  return apiFetch<ClasificacionResponse>("/api/asistente-captura/mecanismo-identidad", {
    method: "POST",
    body: JSON.stringify({ texto_aclaracion: textoAclaracion }),
  });
}

import { apiFetch } from "./httpClient";

export interface GobiernoResponse {
  tenant_id: string;
  nombre: string;
}

// Público, sin sesión -- paso previo a mostrar correo y contraseña.
export function resolverGobierno(clave: string): Promise<GobiernoResponse> {
  return apiFetch<GobiernoResponse>(`/api/gobiernos/${encodeURIComponent(clave)}`, {
    method: "GET",
    sinAuth: true,
  });
}

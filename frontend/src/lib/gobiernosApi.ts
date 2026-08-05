import { apiFetch } from "./httpClient";

export interface GobiernoResponse {
  tenant_id: string;
  nombre: string;
}

// Público, sin sesión (entregables/fase-2/identificacion-gobierno-login.md,
// sección 3) -- paso previo a mostrar los campos de correo y contraseña.
export function resolverGobierno(clave: string): Promise<GobiernoResponse> {
  return apiFetch<GobiernoResponse>(`/api/gobiernos/${encodeURIComponent(clave)}`, {
    method: "GET",
    sinAuth: true,
  });
}

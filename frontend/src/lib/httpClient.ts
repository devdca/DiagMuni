// Envoltorio delgado sobre fetch nativo -- sin axios, TanStack Query ya es la
// capa de data fetching. Rutas relativas "/api/..." funcionan igual en dev
// (proxy de Vite) y en producción (nginx proxea /api al backend).

import { cerrarSesion, obtenerToken } from "./session";

// El guard de sesión de cada pantalla protegida escucha este evento para
// redirigir a /login sin que cada llamada sepa cómo navegar.
export const EVENTO_SESION_EXPIRADA = "diagmuni:sesion-expirada";

export class ApiError extends Error {
  /** Para distinguir 404 (ej. "el plan todavía no existe") de un fallo real. */
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

interface OpcionesApi extends RequestInit {
  sinAuth?: boolean;
}

export async function apiFetch<T>(ruta: string, opciones: OpcionesApi = {}): Promise<T> {
  const { sinAuth, headers, ...resto } = opciones;
  const token = obtenerToken();

  const respuesta = await fetch(ruta, {
    ...resto,
    headers: {
      "Content-Type": "application/json",
      ...(token && !sinAuth ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  // Un 401 con sinAuth=true (ej. login fallido) nunca hubo sesión que expirar.
  if (respuesta.status === 401 && !sinAuth) {
    cerrarSesion();
    window.dispatchEvent(new CustomEvent(EVENTO_SESION_EXPIRADA));
  }

  let cuerpo: unknown = null;
  const texto = await respuesta.text();
  if (texto) {
    try {
      cuerpo = JSON.parse(texto);
    } catch {
      cuerpo = texto;
    }
  }

  if (!respuesta.ok) {
    // "detail" a veces es texto llano y a veces errores de validación (422 de
    // Pydantic) -- solo el texto plano es apto para mostrarse tal cual.
    const detalleCrudo = cuerpo && typeof cuerpo === "object" && "detail" in cuerpo ? cuerpo.detail : null;
    const detalle =
      typeof detalleCrudo === "string" ? detalleCrudo : "No se pudo completar la operación. Intenta de nuevo.";
    throw new ApiError(detalle, respuesta.status);
  }

  return cuerpo as T;
}

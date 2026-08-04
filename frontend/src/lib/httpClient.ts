// Envoltorio delgado sobre fetch nativo (docs/stack-tecnologico.md línea 22-23
// fija TanStack Query como capa de data fetching, no un cliente HTTP nuevo —
// no se agrega axios).
//
// Rutas relativas "/api/..." funcionan igual en desarrollo (proxy de Vite,
// ver vite.config.ts) y en producción (nginx ya proxea /api al backend real,
// docker-compose.yml + nginx/nginx.conf), sin variables de entorno.

import { cerrarSesion, obtenerToken } from "./session";

// Se dispara cuando el backend responde 401 en cualquier llamada — el guard
// de sesión de cada pantalla protegida escucha este evento para redirigir a
// /login sin que cada llamada tenga que saber cómo navegar.
export const EVENTO_SESION_EXPIRADA = "diagmuni:sesion-expirada";

export class ApiError extends Error {}

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

  // Un 401 con sinAuth=true (ej. login con credenciales inválidas) no es una
  // sesión que expira -- nunca hubo sesión. Disparar el evento global aquí
  // provocaría una navegación espuria sobre la propia pantalla de login.
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
    // El backend a veces responde "detail" como texto llano (ej. 401 de
    // credenciales inválidas) y a veces como lista de errores de validación
    // (422 de Pydantic, un objeto/array por campo) -- solo el primer caso es
    // apto para mostrarse tal cual; el segundo cae al mensaje genérico para
    // no exponer texto crudo al funcionario.
    const detalleCrudo =
      cuerpo && typeof cuerpo === "object" && "detail" in cuerpo ? (cuerpo as { detail: unknown }).detail : null;
    const detalle =
      typeof detalleCrudo === "string" ? detalleCrudo : "No se pudo completar la operación. Intenta de nuevo.";
    throw new ApiError(detalle);
  }

  return cuerpo as T;
}

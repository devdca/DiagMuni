// Almacenamiento de sesión del funcionario en el navegador.
//
// El JWT no trae el nombre del gobierno local (ver limitación conocida de F1
// documentada en el reporte de entrega) — por eso "displayName" es un campo
// de texto libre que el propio funcionario escribe en el login, guardado
// junto al token únicamente para poder mostrarlo en la nav.

const TOKEN_KEY = "diagmuni_token";
const DISPLAY_NAME_KEY = "diagmuni_display_name";

export const NOMBRE_GOBIERNO_GENERICO = "Gobierno local";

interface JwtClaims {
  sub: string;
  tenant_id: string;
  rol: string;
  exp: number;
}

function decodeJwtClaims(token: string): JwtClaims | null {
  const partes = token.split(".");
  if (partes.length !== 3) return null;
  try {
    // Los tokens JWT usan base64url; se normaliza a base64 estándar antes de
    // decodificar con atob (sin agregar ninguna librería de JWT en el cliente).
    const base64 = partes[1].replace(/-/g, "+").replace(/_/g, "/");
    const relleno = base64.length % 4 === 0 ? "" : "=".repeat(4 - (base64.length % 4));
    const json = atob(base64 + relleno);
    return JSON.parse(json) as JwtClaims;
  } catch {
    return null;
  }
}

export function guardarSesion(token: string, nombreAMostrar: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(DISPLAY_NAME_KEY, nombreAMostrar.trim());
}

export function cerrarSesion(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(DISPLAY_NAME_KEY);
}

export function obtenerToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function obtenerNombreGobierno(): string {
  const guardado = localStorage.getItem(DISPLAY_NAME_KEY);
  return guardado && guardado.length > 0 ? guardado : NOMBRE_GOBIERNO_GENERICO;
}

// Fuente de verdad de "sesión inválida": token ausente o JWT expirado
// (docs/app-flow.md línea 53). No requiere esperar una respuesta 401 del
// backend para detectar la expiración.
export function sesionValida(): boolean {
  const token = obtenerToken();
  if (!token) return false;
  const claims = decodeJwtClaims(token);
  if (!claims) return false;
  const ahoraEnSegundos = Date.now() / 1000;
  return claims.exp > ahoraEnSegundos;
}

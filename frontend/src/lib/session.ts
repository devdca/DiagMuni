// Almacenamiento de sesión del funcionario en el navegador. El nombre del
// gobierno viaja en el propio JWT (claim "nombre_gobierno").

const TOKEN_KEY = "diagmuni_token";

// Fallback para un token viejo emitido antes de este claim (todavía sin expirar).
export const NOMBRE_GOBIERNO_GENERICO = "Gobierno local";

interface JwtClaims {
  sub: string;
  tenant_id: string;
  nombre_gobierno: string;
  pais: string;
  nivel_gobierno: string;
  rol: string;
  exp: number;
}

function decodeJwtClaims(token: string): JwtClaims | null {
  const partes = token.split(".");
  if (partes.length !== 3) return null;
  try {
    // JWT usa base64url; se normaliza a base64 estándar para decodificar con atob.
    const base64 = partes[1].replace(/-/g, "+").replace(/_/g, "/");
    const relleno = base64.length % 4 === 0 ? "" : "=".repeat(4 - (base64.length % 4));
    const json = atob(base64 + relleno);
    return JSON.parse(json) as JwtClaims;
  } catch {
    return null;
  }
}

export function guardarSesion(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function cerrarSesion(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function obtenerToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function obtenerNombreGobierno(): string {
  const token = obtenerToken();
  if (!token) return NOMBRE_GOBIERNO_GENERICO;
  const claims = decodeJwtClaims(token);
  return claims?.nombre_gobierno && claims.nombre_gobierno.length > 0 ? claims.nombre_gobierno : NOMBRE_GOBIERNO_GENERICO;
}

// Solo para decidir qué mostrar (ej. opciones de mecanismo_identidad en F3) --
// nunca para seguridad, el backend siempre resuelve `pais` desde `Tenant`.
// `null` (no un país adivinado) si el token es viejo y no trae el claim.
export function obtenerPais(): string | null {
  const token = obtenerToken();
  if (!token) return null;
  const claims = decodeJwtClaims(token);
  return claims?.pais && claims.pais.length > 0 ? claims.pais : null;
}

// Mismo criterio que obtenerPais -- "municipal" | "estatal" | "federal", solo UI.
export function obtenerNivelGobierno(): string | null {
  const token = obtenerToken();
  if (!token) return null;
  const claims = decodeJwtClaims(token);
  return claims?.nivel_gobierno && claims.nivel_gobierno.length > 0 ? claims.nivel_gobierno : null;
}

// Solo para la nav (ej. link "Administración") -- cada endpoint /api/admin/*
// vuelve a exigir el rol real desde la base de datos.
export function obtenerRol(): string | null {
  const token = obtenerToken();
  if (!token) return null;
  const claims = decodeJwtClaims(token);
  return claims?.rol && claims.rol.length > 0 ? claims.rol : null;
}

export function esAdmin(): boolean {
  return obtenerRol() === "admin_gobierno";
}

// Detecta expiración sin esperar un 401 del backend.
export function sesionValida(): boolean {
  const token = obtenerToken();
  if (!token) return false;
  const claims = decodeJwtClaims(token);
  if (!claims) return false;
  const ahoraEnSegundos = Date.now() / 1000;
  return claims.exp > ahoraEnSegundos;
}

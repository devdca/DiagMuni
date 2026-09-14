// Almacenamiento de sesión del funcionario en el navegador.
//
// El nombre del gobierno local viaja en el propio JWT (claim "nombre_gobierno",
// entregables/fase-2/identificacion-gobierno-login.md, sección 4) -- ya no es un
// campo de texto libre que el funcionario escribe a mano (limitación conocida de
// F1, ya resuelta).

const TOKEN_KEY = "diagmuni_token";

// Manejo defensivo: un JWT sin el claim "nombre_gobierno" no debería ocurrir en
// operación normal (todo token nuevo lo trae, ver backend/app/core/security.py),
// pero un token viejo emitido antes de este cambio (mismo `jwt_secret`, todavía
// sin expirar) sí podría carecer de él -- se prefiere este texto genérico a
// romper la nav en ese caso de borde transitorio.
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

// "mx" | "uy" -- claim nuevo del JWT (backend/app/core/security.py::create_access_token),
// solo para que el frontend sepa qué mostrar (ej. qué opción de mecanismo_identidad
// ofrecer en el cuestionario, F3). Nunca se usa para decidir nada de seguridad: el
// backend siempre vuelve a resolver `pais` desde `Tenant`, nunca confía en este claim.
//
// Devuelve `null` (no un país adivinado) si el token es viejo y no trae el claim
// todavía -- mismo caso de borde transitorio que `NOMBRE_GOBIERNO_GENERICO`, pero
// acá no hay un valor genérico seguro: mostrar el país equivocado ofrecería una
// opción de mecanismo de identidad que no le corresponde a ese gobierno.
export function obtenerPais(): string | null {
  const token = obtenerToken();
  if (!token) return null;
  const claims = decodeJwtClaims(token);
  return claims?.pais && claims.pais.length > 0 ? claims.pais : null;
}

// "municipal" | "estatal" | "federal" -- claim nuevo del JWT (migración 0018),
// ortogonal a `pais`, mismo criterio de arriba: solo para que el frontend sepa
// qué mostrar (ej. opciones de mecanismo_identidad a nivel federal), nunca para
// decidir nada de seguridad. `null` si el token es viejo y no trae el claim
// todavía (mismo caso de borde transitorio que `obtenerPais`).
export function obtenerNivelGobierno(): string | null {
  const token = obtenerToken();
  if (!token) return null;
  const claims = decodeJwtClaims(token);
  return claims?.nivel_gobierno && claims.nivel_gobierno.length > 0 ? claims.nivel_gobierno : null;
}

// "funcionario" | "admin_gobierno" (RBAC, migración 0011 del backend). Solo para
// decidir qué mostrar en la nav (ej. el link "Administración") -- nunca para
// autorizar nada: cada endpoint de /api/admin/* vuelve a exigir el rol real
// desde la base de datos (app/adaptadores/http/deps.py::requerir_admin), igual
// que `pais` nunca se usa para decidir seguridad (ver obtenerPais arriba).
export function obtenerRol(): string | null {
  const token = obtenerToken();
  if (!token) return null;
  const claims = decodeJwtClaims(token);
  return claims?.rol && claims.rol.length > 0 ? claims.rol : null;
}

export function esAdmin(): boolean {
  return obtenerRol() === "admin_gobierno";
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

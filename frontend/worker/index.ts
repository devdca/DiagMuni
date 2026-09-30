// Worker del preview de PR: sirve el build de la SPA y proxea al backend.
//
// Existe porque el frontend llama al backend con rutas relativas ("/api/...",
// ver src/lib/httpClient.ts) y el backend no tiene CORS configurado: un preview
// que sirviera solo los estáticos dejaría la SPA sin API y sin forma de
// alcanzarla. Replicar el mismo origen acá evita tanto tocar httpClient como
// abrir CORS en un backend multi-tenant.
//
// El reparto de rutas es el mismo de nginx/nginx.conf en producción: "/api/" y
// "/health" van al backend, todo lo demás sale de los estáticos con fallback a
// index.html (`not_found_handling: single-page-application` en wrangler.jsonc).
// Nunca es destino de producción -- docs/stack-tecnologico.md limita Cloudflare
// a previews de desarrollo.

interface Env {
  ASSETS: { fetch(request: Request): Promise<Response> };
  // URL pública del backend de preview. Sin ella el preview sigue siendo útil
  // para revisar maquetación, pero la API responde 503 en vez de fallar con un
  // 404 de estáticos, que sería indistinguible de un error de ruteo.
  PREVIEW_BACKEND_URL?: string;
}

function vaAlBackend(pathname: string): boolean {
  return pathname.startsWith("/api/") || pathname === "/health";
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (!vaAlBackend(url.pathname)) {
      return env.ASSETS.fetch(request);
    }

    const base = env.PREVIEW_BACKEND_URL?.trim();
    if (!base) {
      return Response.json(
        {
          detail:
            "Este preview no tiene backend configurado (falta la variable PREVIEW_BACKEND_URL). " +
            "Solo sirve para revisar la interfaz.",
        },
        { status: 503 },
      );
    }

    const destino = new URL(url.pathname + url.search, base);
    return fetch(new Request(destino, request));
  },
};

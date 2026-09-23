import * as Sentry from "@sentry/react";

// Captura de errores de JS en producción. Alcance mínimo a propósito: solo
// excepciones/promesas rechazadas, sin tracing ni session replay.
// `VITE_SENTRY_DSN` es una variable de BUILD (no runtime) -- si no está
// configurada, esta función no hace nada (ni init, ni listeners, ni red).
export function inicializarSentry(): void {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) return;

  Sentry.init({
    dsn,
    // Explícito: nunca mandar datos que identifiquen al funcionario.
    sendDefaultPii: false,
    // Defensa en profundidad: por si el JWT o un body de formulario se
    // colara en una breadcrumb de fetch/xhr, se descarta antes de salir.
    beforeBreadcrumb(breadcrumb) {
      if (breadcrumb.category === "fetch" || breadcrumb.category === "xhr") {
        delete breadcrumb.data?.["input"];
        delete breadcrumb.data?.["body"];
        delete breadcrumb.data?.["Authorization"];
      }
      return breadcrumb;
    },
  });
}

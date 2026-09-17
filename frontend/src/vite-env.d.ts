/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Opcional -- ver frontend/src/lib/sentry.ts. Ausente/vacía: Sentry.init nunca
  // se llama, mismo comportamiento de hoy (sin captura de errores en producción).
  readonly VITE_SENTRY_DSN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

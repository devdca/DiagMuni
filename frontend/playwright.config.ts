import { defineConfig, devices } from "@playwright/test";

import { ARCHIVO_ESTADO_SESION } from "./e2e/estado-sesion";

// E2E contra el stack Docker real (docs/runbook-despliegue.md), no contra `vite dev`
// -- el objetivo es probar el mismo nginx + backend que corre en producción.
// BASE_URL permite apuntar a otro puerto si 8090 ya está tomado (mismo caso que
// documenta el runbook para el mapeo de nginx).
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // los specs comparten un solo tenant de prueba, evitar carreras
  // El cuestionario pasó de 6 a 21 preguntas (expansión a tres órdenes de
  // gobierno): el recorrido encadenado hace ~4x más clics que cuando se fijó
  // el default de 30 s, que quedó sin margen.
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:8090",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    // El login real corre una sola vez por corrida (ver e2e/auth.setup.ts) y deja
    // la sesión en disco: `/api/auth/login` admite 5 intentos por minuto por IP y
    // un login por spec, con reintentos, se acerca a ese techo.
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], storageState: ARCHIVO_ESTADO_SESION },
      dependencies: ["setup"],
    },
  ],
});

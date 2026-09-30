import { expect, test as setup } from "@playwright/test";

import { ARCHIVO_ESTADO_SESION } from "./estado-sesion";
import { iniciarSesion } from "./flujo";

// Proyecto de setup: hace el login real UNA vez por corrida y guarda la sesión
// para que los specs arranquen autenticados.
//
// El motivo es un límite real del backend, no una optimización: `/api/auth/login`
// admite 5 intentos por minuto por IP (backend/app/core/rate_limit.py). Con un
// login por spec más los reintentos de CI, dos specs ya rozan ese techo y el
// tercero que se agregue empezaría a dar 429 intermitentes -- el tipo de
// inestabilidad que termina con alguien sacando el job de los checks requeridos.
//
// El login no pierde cobertura: se ejercita acá, con sus aserciones, en vez de
// repetirse en cada spec. La sesión vive en localStorage (src/lib/session.ts),
// que es lo que `storageState` persiste.
setup("login de dos pasos y sesión guardada", async ({ page }) => {
  await iniciarSesion(page);

  const token = await page.evaluate(() => window.localStorage.getItem("diagmuni_token"));
  expect(token, "el login no dejó token en localStorage").toBeTruthy();

  await page.context().storageState({ path: ARCHIVO_ESTADO_SESION });
});

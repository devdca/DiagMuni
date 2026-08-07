import { expect, test } from "@playwright/test";

import { credenciales } from "./credenciales";

// Recorre las 6 pantallas del mapa de docs/app-flow.md en un solo flujo
// encadenado (login -> alta de trámite -> diagnóstico -> plan -> seguimiento ->
// perfil), igual que la verificación manual que reemplaza. Un solo test en vez
// de varios independientes porque cada pantalla depende del estado que deja la
// anterior (el trámite creado, el diagnóstico enviado, el plan generado).
test("recorrido completo de un gobierno nuevo", async ({ page }) => {
  const nombreTramite = `Licencia de funcionamiento E2E ${Date.now()}`;

  await test.step("login en dos pasos", async () => {
    await page.goto("/login");
    await page.getByRole("textbox", { name: "Clave del gobierno" }).fill(credenciales.claveGobierno);
    await page.getByRole("button", { name: "Continuar" }).click();

    await page.getByRole("textbox", { name: "Correo electrónico" }).fill(credenciales.email);
    await page.getByRole("textbox", { name: "Contraseña" }).fill(credenciales.password);
    await page.getByRole("button", { name: "Ingresar" }).click();

    await expect(page).toHaveURL("/");
  });

  await test.step("alta de trámite en el panel resumen", async () => {
    await page.getByRole("button", { name: "Agregar trámite" }).click();
    await page.getByRole("textbox", { name: "Nombre del trámite" }).fill(nombreTramite);
    await page.getByRole("button", { name: "Guardar" }).click();

    const fila = page.getByRole("row", { name: new RegExp(nombreTramite) });
    await expect(fila).toBeVisible();
    await fila.getByRole("button", { name: "Continuar diagnóstico" }).click();
    await expect(page).toHaveURL(/\/tramites\/.+\/diagnostico/);
  });

  await test.step("cuestionario de diagnóstico completo", async () => {
    // Cualquier combinación de respuestas es válida para el motor -- basta con
    // responder las 6, sin importar el valor. "No" a las 5 booleanas + "Ninguno"
    // para el mecanismo de identidad. `exact: true` + scoping por radiogroup es
    // obligatorio acá: "Ninguno" contiene "no" como substring, así que
    // `getByRole("radio", { name: "No" })` sin exact también matchea esa opción.
    // `.count()` no espera a que React termine de hidratar el cuestionario (es
    // navegación SPA, no una carga de página) -- sin esta espera devuelve 0 de
    // inmediato y el loop de abajo nunca se ejecuta.
    const grupos = page.getByRole("radiogroup");
    await expect(grupos.first()).toBeVisible();
    const totalGrupos = await grupos.count();
    for (let i = 0; i < totalGrupos - 1; i++) {
      await grupos.nth(i).getByRole("radio", { name: "No", exact: true }).click();
    }
    await grupos.last().getByRole("radio", { name: "Ninguno", exact: true }).click();

    await expect(page.getByText("6 de 6 preguntas respondidas")).toBeVisible();

    const enviar = page.getByRole("button", { name: "Enviar diagnóstico" });
    await expect(enviar).toBeEnabled();
    await enviar.click();

    await expect(page).toHaveURL(/\/tramites\/.+\/plan/, { timeout: 30_000 });
  });

  await test.step("plan de modernización con detalle de brechas", async () => {
    await expect(page.getByText("Plan de modernización")).toBeVisible();
    const primeraBrecha = page.getByRole("button", { name: /Bloquea|Refuerza|Requisito/ }).first();
    await primeraBrecha.click();
    await expect(page.getByText("Fuente normativa:")).toBeVisible();

    await page.getByRole("button", { name: "Ir al seguimiento" }).click();
    await expect(page).toHaveURL("/seguimiento");
  });

  await test.step("cambiar estado de una acción en seguimiento", async () => {
    const primeraFila = page.getByRole("row").filter({ hasText: nombreTramite }).first();
    const semaforo = primeraFila.getByLabel("Cambiar estado del semáforo");
    await semaforo.selectOption("Completado");
    // No usar getByText("Completado") acá: matchea tanto la etiqueta visible como
    // la <option> oculta del propio <select>, modo estricto lo rechaza.
    await expect(semaforo).toHaveValue("completado");
  });

  await test.step("perfil del gobierno autoguarda", async () => {
    await page.getByRole("link", { name: "Perfil del gobierno" }).click();
    await expect(page).toHaveURL("/gobierno/perfil");

    const respuestaGuardada = page.waitForResponse(
      (respuesta) => respuesta.url().includes("/api/gobierno/contexto") && respuesta.request().method() === "PUT",
    );
    // Valor distinto en cada corrida a propósito -- si coincide con el que ya
    // había (ej. al reintentar contra un tenant no efímero), React no dispara
    // onChange y el PUT nunca sale, dejando el waitForResponse colgado.
    await page.getByRole("spinbutton").first().fill(String(10_000 + (Date.now() % 90_000)));
    await page.getByRole("spinbutton").first().blur();
    // `toBeOK()` es para `APIResponse` (de request.get()/post()) -- el objeto que
    // devuelve `page.waitForResponse()` es un `Response` de página, con `.ok()`
    // como método normal, no como matcher.
    expect((await respuestaGuardada).ok()).toBeTruthy();
  });
});

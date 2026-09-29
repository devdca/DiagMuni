import { expect, test } from "@playwright/test";

import {
  completarYEnviarDiagnostico,
  crearTramiteYAbrirDiagnostico,
  responderParcialYEsperarAutoguardado,
} from "./flujo";

// Recorre el camino principal del mapa de docs/app-flow.md en un solo flujo
// encadenado (login -> alta de trámite -> diagnóstico -> plan -> seguimiento ->
// perfil), igual que la verificación manual que reemplaza. Un solo test en vez
// de varios independientes porque cada pantalla depende del estado que deja la
// anterior (el trámite creado, el diagnóstico enviado, el plan generado).
//
// Ejercita el modo degradado (sin IA disponible en este entorno) -- el modo
// llm tiene su propio spec, modo-llm.spec.ts, porque requiere infraestructura
// real opcional (Ollama) que no siempre está disponible.
test("recorrido completo de un gobierno nuevo", async ({ page }) => {
  const nombreTramite = `Licencia de funcionamiento E2E ${Date.now()}`;

  // El login corre en el proyecto de setup (e2e/auth.setup.ts), una sola vez por
  // corrida; acá se arranca ya autenticado en el panel de resumen.
  await page.goto("/");

  await test.step("alta de trámite en el panel resumen", () => crearTramiteYAbrirDiagnostico(page, nombreTramite));

  await test.step("guardar parcial y reanudar tras recargar", async () => {
    const respondidas = await responderParcialYEsperarAutoguardado(page, 3);

    await page.reload();

    // El autoguardado por campo solo sirve de algo si lo capturado sobrevive a
    // que el funcionario cierre la pestaña y vuelva después.
    for (const variable of respondidas) {
      await expect(page.locator(`#${variable}-no`)).toBeChecked();
    }
  });

  await test.step("cuestionario de diagnóstico completo", () => completarYEnviarDiagnostico(page));

  await test.step("plan de modernización con detalle de brechas", async () => {
    await expect(page.getByText("Plan de modernización")).toBeVisible();

    // El plan se divide en pestañas y abre en "Resumen ejecutivo"; el acordeón
    // por brecha vive en "Detalle técnico" (Plan.tsx, TabsContent value="tecnico").
    await page.getByRole("tab", { name: "Detalle técnico" }).click();

    const primeraBrecha = page.getByRole("button", { name: /Bloquea|Refuerza|Requisito/ }).first();
    await primeraBrecha.click();
    await expect(page.getByText("Fuente normativa:")).toBeVisible();

    await page.getByRole("button", { name: "Ir al seguimiento" }).click();
    await expect(page).toHaveURL("/seguimiento");
  });

  await test.step("cambiar estado de una acción en seguimiento", async () => {
    // Anclar la fila por la descripción de su acción, no por `.first()`. El
    // endpoint ya ordena de forma determinista, pero `.first()` seguiría siendo
    // frágil: el orden es por fecha objetivo, así que cualquier cambio en las
    // fechas que genere el plan movería la fila. Se fija la acción concreta que
    // se va a cambiar.
    const descripcion = (
      await page.getByRole("row").filter({ hasText: nombreTramite }).first().locator("p").first().innerText()
    ).trim();

    // Los dos filtros son necesarios: la descripción viene del catálogo, así que
    // se repite en cada trámite diagnosticado, y el nombre del trámite por sí
    // solo cubre sus 21 acciones.
    const fila = page.getByRole("row").filter({ hasText: nombreTramite }).filter({ hasText: descripcion });
    const semaforo = fila.getByLabel("Cambiar estado del semáforo");
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

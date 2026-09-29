import { expect, type Page } from "@playwright/test";

import { credenciales } from "./credenciales";

// Pasos compartidos entre flujo-completo.spec.ts (modo degradado) y
// modo-llm.spec.ts (modo llm, docs/plan-implementacion.md Fase G1) -- ambos
// recorren exactamente el mismo camino hasta el envío del diagnóstico, solo
// cambia qué hay configurado en OLLAMA_API_BASE/LLM_PROVIDER al momento de
// generar el plan.

export async function iniciarSesion(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "Clave del gobierno" }).fill(credenciales.claveGobierno);
  await page.getByRole("button", { name: "Continuar" }).click();

  await page.getByRole("textbox", { name: "Correo electrónico" }).fill(credenciales.email);
  await page.getByRole("textbox", { name: "Contraseña" }).fill(credenciales.password);
  await page.getByRole("button", { name: "Ingresar" }).click();

  await expect(page).toHaveURL("/");
}

export async function crearTramiteYAbrirDiagnostico(page: Page, nombreTramite: string): Promise<void> {
  await page.getByRole("button", { name: "Agregar trámite" }).click();
  await page.getByRole("textbox", { name: "Nombre del trámite" }).fill(nombreTramite);
  await page.getByRole("button", { name: "Guardar" }).click();

  const fila = page.getByRole("row", { name: new RegExp(nombreTramite) });
  await expect(fila).toBeVisible();
  await fila.getByRole("button", { name: "Continuar diagnóstico" }).click();
  await expect(page).toHaveURL(/\/tramites\/.+\/diagnostico/);
}

// Variables booleanas cuyo criterio de detección dispara con `true` en vez de
// con `false` (backend/app/dominio/reglas/*.yaml). Para ellas "Sí" es la
// respuesta que abre brecha y "No" la conforme, al revés que el resto.
const BOOLEANAS_INVERTIDAS = new Set(["proteccion_datos_incompleta"]);

// `#concurrente-si|no` usa el mismo componente que las preguntas booleanas
// (CampoBooleanoRadio con idPrefix), pero es contexto opcional del trámite, no
// una variable del catálogo: no cuenta para "N de N" ni genera brechas.
const PREFIJOS_NO_CATALOGO = new Set(["concurrente"]);

/** Nombres de las variables booleanas presentes en el cuestionario, leídos del
 * DOM. No asume cuántas son ni en qué orden aparecen: el catálogo crece (7 -> 29
 * variables entre julio y septiembre de 2026) y anclarse a la posición fue
 * justamente lo que rompió este helper. El contrato estable es el nombre de la
 * variable, compartido por los YAML del motor, el JSON de `respuestas` y los
 * `id` del DOM (ver frontend/src/components/ui/campo-booleano-radio.tsx). */
async function variablesBooleanas(page: Page): Promise<string[]> {
  const ids = await page.locator('[role="radio"][id$="-si"]').evaluateAll((nodos) =>
    nodos.map((n) => n.id.replace(/-si$/, "")),
  );
  return ids.filter((variable) => !PREFIJOS_NO_CATALOGO.has(variable));
}

export async function completarYEnviarDiagnostico(
  page: Page,
  opciones?: {
    /** Variables que deben quedar en estado de brecha. `"todas"` abre brecha en
     * cada booleana -- útil en modo degradado, donde generar el plan es
     * instantáneo. Una lista corta es lo que necesita modo-llm.spec.ts: cada
     * brecha dispara su propia llamada al LLM (generación + verificación) y
     * contra Ollama/phi3 sin GPU cada una cuesta decenas de segundos. */
    brechas?: string[] | "todas";
    mecanismo?: string;
    timeoutPlanMs?: number;
  },
): Promise<void> {
  // `.count()`/`evaluateAll` no esperan a que React termine de hidratar el
  // cuestionario (es navegación SPA, no carga de página): sin esta espera la
  // lista sale vacía y no se responde nada.
  await expect(page.getByRole("radiogroup").first()).toBeVisible();

  const brechas = opciones?.brechas ?? "todas";
  const booleanas = await variablesBooleanas(page);
  expect(booleanas.length, "el cuestionario no expuso ninguna pregunta booleana").toBeGreaterThan(0);

  for (const variable of booleanas) {
    const abreBrecha = brechas === "todas" || brechas.includes(variable);
    const invertida = BOOLEANAS_INVERTIDAS.has(variable);
    await page.locator(`#${variable}-${abreBrecha !== invertida ? "no" : "si"}`).click();
  }

  // Contexto opcional: no cuenta para el contador, pero se responde para que el
  // diagnóstico enviado se parezca al de un funcionario real.
  await page.locator("#volumen-100_1000").click();
  await page.locator("#concurrente-no").click();

  // El autoguardado por campo hace PUT 1500 ms después del último cambio. Si se
  // pulsa "Enviar" dentro de esa ventana, el PUT puede llegar después del POST
  // y devolver el trámite a `en_progreso` mientras el plan se genera (ver
  // guardar_diagnostico en backend/app/adaptadores/http/diagnosticos.py, que
  // cambia el estado sin el guard de 409 que sí tiene `enviar`). Esperar el PUT
  // antes de enviar quita esa carrera del test; cerrarla en el producto es otro
  // cambio.
  //
  // La promesa se registra ANTES del último clic a propósito: el debounce puede
  // vencer mientras se evalúa el contador, y `waitForResponse` solo ve
  // respuestas posteriores a su registro.
  const guardado = page.waitForResponse(
    (r) => r.request().method() === "PUT" && /\/diagnostico$/.test(new URL(r.url()).pathname),
  );
  await page.locator(`#mecanismo-${opciones?.mecanismo ?? "ninguno"}`).click();

  // Sin fijar el total: el contador dice "N de N" y N cambia con el catálogo y
  // con las variables que excluya el tipo de trámite.
  await expect(page.getByText(/^(\d+) de \1 preguntas respondidas$/)).toBeVisible();

  await guardado;

  const enviar = page.getByRole("button", { name: "Enviar diagnóstico" });
  await expect(enviar).toBeEnabled();
  await enviar.click();

  await expect(page).toHaveURL(/\/tramites\/.+\/plan/, { timeout: opciones?.timeoutPlanMs ?? 30_000 });
}

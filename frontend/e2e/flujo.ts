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

export async function completarYEnviarDiagnostico(page: Page, opciones?: { timeoutPlanMs?: number }): Promise<void> {
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

  await expect(page).toHaveURL(/\/tramites\/.+\/plan/, { timeout: opciones?.timeoutPlanMs ?? 30_000 });
}

// Variante de una sola brecha, solo para modo-llm.spec.ts -- cada brecha
// dispara su propia llamada al LLM (generación + verificación); en modo
// degradado da igual (es instantáneo), pero contra Ollama/phi3 real sin GPU
// (~76-123s por llamada, docs/TRD.md) cada brecha extra multiplica el tiempo
// de espera. "Sí"/"No" por pregunta según backend/app/engine/reglas/*.yaml
// (criterio_deteccion de cada regla) para que solo "firma_electronica" dispare:
// documentos_digitalizados=Sí, motor_pagos=Sí, firma_electronica_habilitada=No,
// interoperabilidad=Sí, proteccion_datos_incompleta=No (criterio pide =true
// para disparar, "No" es la respuesta conforme), mecanismo_identidad="Llave MX".
export async function completarDiagnosticoConUnaSolaBrechaYEnviar(
  page: Page,
  opciones?: { timeoutPlanMs?: number },
): Promise<void> {
  const grupos = page.getByRole("radiogroup");
  await expect(grupos.first()).toBeVisible();

  const respuestasBooleanas = ["Sí", "Sí", "No", "Sí", "No"] as const;
  for (const [indice, respuesta] of respuestasBooleanas.entries()) {
    await grupos.nth(indice).getByRole("radio", { name: respuesta, exact: true }).click();
  }
  await grupos.last().getByRole("radio", { name: "Llave MX", exact: true }).click();

  await expect(page.getByText("6 de 6 preguntas respondidas")).toBeVisible();

  const enviar = page.getByRole("button", { name: "Enviar diagnóstico" });
  await expect(enviar).toBeEnabled();
  await enviar.click();

  await expect(page).toHaveURL(/\/tramites\/.+\/plan/, { timeout: opciones?.timeoutPlanMs ?? 30_000 });
}

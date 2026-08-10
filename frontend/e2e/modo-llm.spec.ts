import { expect, test } from "@playwright/test";

import { completarDiagnosticoConUnaSolaBrechaYEnviar, crearTramiteYAbrirDiagnostico, iniciarSesion } from "./flujo";

// Margen sobre los 76-123s medidos contra phi3 sin GPU (docs/TRD.md) para UNA
// sola llamada -- el diagnóstico de este test dispara una sola brecha a
// propósito (completarDiagnosticoConUnaSolaBrechaYEnviar) para necesitar solo
// una generación + una verificación, no 4-5 -- con varias brechas el tiempo
// se multiplica y ni este margen alcanza (falló así en la primera corrida real).
const TIMEOUT_PLAN_LLM_MS = 300_000;

async function ollamaConPhi3Disponible(): Promise<boolean> {
  try {
    const respuesta = await fetch("http://localhost:11434/api/tags");
    if (!respuesta.ok) return false;
    const datos: { models?: Array<{ name?: string }> } = await respuesta.json();
    return (datos.models ?? []).some((modelo) => modelo.name?.startsWith("phi3"));
  } catch {
    return false;
  }
}

// Complementa flujo-completo.spec.ts (que solo ejercita modo degradado) --
// docs/plan-implementacion.md Fase G1 pide E2E "en modo degradado y en modo
// LLM". Requiere el perfil `ia-local` de docker-compose.yml activo con `phi3`
// ya descargado y OLLAMA_API_BASE=http://ollama:11434 en el `.env` del backend
// (docs/runbook-despliegue.md, "IA local con Ollama") -- se salta limpio si no
// está disponible, mismo estándar que backend/tests/test_generador_plan_ollama_real.py:
// nunca falla el pipeline por la ausencia de infraestructura real opcional.
test("plan generado en modo llm no muestra el aviso de modo degradado", async ({ page }) => {
  test.skip(
    !(await ollamaConPhi3Disponible()),
    "Requiere el perfil ia-local de docker-compose.yml activo con phi3 descargado " +
      "(docker compose --profile ia-local up -d && docker compose exec ollama ollama pull phi3) " +
      "y OLLAMA_API_BASE=http://ollama:11434 en .env (con el backend recreado después).",
  );
  test.setTimeout(TIMEOUT_PLAN_LLM_MS + 60_000);

  const nombreTramite = `Licencia de funcionamiento E2E modo-llm ${Date.now()}`;

  await iniciarSesion(page);
  await crearTramiteYAbrirDiagnostico(page, nombreTramite);
  await completarDiagnosticoConUnaSolaBrechaYEnviar(page, { timeoutPlanMs: TIMEOUT_PLAN_LLM_MS });

  await expect(page.getByText("Plan de modernización")).toBeVisible();
  // Único indicador que expone Plan.tsx (`data.modo === "degradado"`) -- su
  // ausencia es la señal de que el plan sí vino de la ruta LLM/verificador,
  // no de la plantilla determinista.
  await expect(page.getByText("Este plan se generó con nuestras plantillas internas")).toHaveCount(0);
});

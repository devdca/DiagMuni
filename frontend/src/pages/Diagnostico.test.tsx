import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/httpClient";
import { mensajeDeError } from "./Diagnostico";

// Regresión directa del parche de seguridad del 7-sep (H-11): un 429
// reintentado de inmediato vuelve a fallar, así que el genérico "intenta de
// nuevo" es mal consejo ahí -- 409/429 deben mostrar su propio `detail` en
// lenguaje llano, cualquier otro error cae al mensaje genérico.
describe("mensajeDeError", () => {
  it("muestra el detail del backend para un 409 (plan en curso)", () => {
    const error = new ApiError("El plan de este trámite todavía se está generando.", 409);
    expect(mensajeDeError(error)).toBe("El plan de este trámite todavía se está generando.");
  });

  it("muestra el detail del backend para un 429 (cooldown), no el genérico", () => {
    const error = new ApiError("Demasiados envíos. Espera un momento e intenta de nuevo.", 429);
    expect(mensajeDeError(error)).toBe("Demasiados envíos. Espera un momento e intenta de nuevo.");
  });

  it("usa el mensaje genérico para cualquier otro status de ApiError", () => {
    const error = new ApiError("Internal Server Error", 500);
    expect(mensajeDeError(error)).toBe("No se pudo completar la operación. Intenta de nuevo.");
  });

  it("usa el mensaje genérico si el error no es un ApiError", () => {
    expect(mensajeDeError(new Error("fallo de red"))).toBe("No se pudo completar la operación. Intenta de nuevo.");
    expect(mensajeDeError(null)).toBe("No se pudo completar la operación. Intenta de nuevo.");
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CampoBooleanoRadio } from "./campo-booleano-radio";

// Este componente sostiene un contrato que no se ve desde acá: los `id` que
// emite (`${idPrefix}-si` / `${idPrefix}-no`) son los selectores con los que
// frontend/e2e/flujo.ts responde el cuestionario completo, y `idPrefix` es
// siempre el nombre de la variable del catálogo. Ese anclaje es lo que permite
// que el E2E sobreviva a que el catálogo crezca, en vez de depender del orden
// de las preguntas en el DOM -- que fue exactamente lo que lo rompió cuando el
// cuestionario pasó de 6 a 21 preguntas. Si alguien cambia el esquema de `id`,
// el E2E falla con un timeout opaco en otro archivo; este test lo convierte en
// un fallo directo y localizado.
describe("CampoBooleanoRadio", () => {
  it("emite ids `${idPrefix}-si` y `${idPrefix}-no` (contrato con el E2E)", () => {
    render(<CampoBooleanoRadio valor={null} onCambiar={vi.fn()} idPrefix="firma_electronica_habilitada" />);

    expect(document.querySelector("#firma_electronica_habilitada-si")).not.toBeNull();
    expect(document.querySelector("#firma_electronica_habilitada-no")).not.toBeNull();
  });

  it("asocia cada etiqueta visible con su opción, para que el clic en el texto funcione", async () => {
    const onCambiar = vi.fn();
    render(<CampoBooleanoRadio valor={null} onCambiar={onCambiar} idPrefix="motor_pagos" />);

    await userEvent.click(screen.getByText("Sí"));
    expect(onCambiar).toHaveBeenCalledWith(true);

    await userEvent.click(screen.getByText("No"));
    expect(onCambiar).toHaveBeenLastCalledWith(false);
  });

  it("no pasa de no controlado a controlado cuando llega el valor guardado", () => {
    // Con `value={undefined}` React trata el RadioGroup como no controlado y
    // avisa en consola al recibir el primer valor real. Pasa siempre que el
    // autoguardado rehidrata una respuesta ya capturada.
    const avisos: unknown[] = [];
    const errorOriginal = console.error;
    console.error = (...args: unknown[]) => avisos.push(args[0]);

    try {
      const { rerender } = render(<CampoBooleanoRadio valor={null} onCambiar={vi.fn()} idPrefix="disponible_movil" />);
      rerender(<CampoBooleanoRadio valor={true} onCambiar={vi.fn()} idPrefix="disponible_movil" />);
    } finally {
      console.error = errorOriginal;
    }

    const cambioDeControl = avisos.some(
      (aviso) => typeof aviso === "string" && aviso.includes("uncontrolled to controlled"),
    );
    expect(cambioDeControl).toBe(false);
  });
});

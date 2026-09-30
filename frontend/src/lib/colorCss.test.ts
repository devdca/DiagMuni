import { describe, expect, it } from "vitest";

import { resolverColorCss } from "./colorCss";

describe("resolverColorCss", () => {
  it("devuelve el valor tal cual si no es un var(--token)", () => {
    expect(resolverColorCss("#0d770d")).toBe("#0d770d");
  });

  it("no revienta si el patrón var() no matchea (formato inesperado)", () => {
    expect(resolverColorCss("var(sin-guiones)")).toBe("var(sin-guiones)");
  });
});

import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAutoguardadoCampo } from "./useAutoguardadoCampo";

describe("useAutoguardadoCampo", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("no guarda en el render inicial", () => {
    const guardar = vi.fn().mockResolvedValue(undefined);
    renderHook(() => useAutoguardadoCampo("valor inicial", guardar));

    vi.advanceTimersByTime(5000);

    expect(guardar).not.toHaveBeenCalled();
  });

  it("guarda con el valor nuevo después del debounce", async () => {
    const guardar = vi.fn().mockResolvedValue(undefined);
    const { rerender } = renderHook(({ valor }) => useAutoguardadoCampo(valor, guardar, 1000), {
      initialProps: { valor: "a" },
    });

    rerender({ valor: "b" });
    expect(guardar).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(1000);

    expect(guardar).toHaveBeenCalledTimes(1);
    expect(guardar).toHaveBeenCalledWith("b");
  });

  it("cancela el guardado pendiente si el valor cambia de nuevo antes del debounce", async () => {
    const guardar = vi.fn().mockResolvedValue(undefined);
    const { rerender } = renderHook(({ valor }) => useAutoguardadoCampo(valor, guardar, 1000), {
      initialProps: { valor: "a" },
    });

    rerender({ valor: "b" });
    vi.advanceTimersByTime(600);
    rerender({ valor: "c" });

    await vi.advanceTimersByTimeAsync(1000);

    expect(guardar).toHaveBeenCalledTimes(1);
    expect(guardar).toHaveBeenCalledWith("c");
  });

  it("cancela el timer pendiente si el componente se desmonta", () => {
    const guardar = vi.fn().mockResolvedValue(undefined);
    const { rerender, unmount } = renderHook(({ valor }) => useAutoguardadoCampo(valor, guardar, 1000), {
      initialProps: { valor: "a" },
    });

    rerender({ valor: "b" });
    unmount();

    vi.advanceTimersByTime(2000);

    expect(guardar).not.toHaveBeenCalled();
  });

  it("pasa por guardando y termina en guardado cuando guardar resuelve", async () => {
    const guardar = vi.fn().mockResolvedValue(undefined);
    const { result, rerender } = renderHook(({ valor }) => useAutoguardadoCampo(valor, guardar, 1000), {
      initialProps: { valor: "a" },
    });

    rerender({ valor: "b" });
    await vi.advanceTimersByTimeAsync(1000);

    expect(result.current).toBe("guardado");
  });

  it("termina en error cuando guardar rechaza", async () => {
    const guardar = vi.fn().mockRejectedValue(new Error("falló"));
    const { result, rerender } = renderHook(({ valor }) => useAutoguardadoCampo(valor, guardar, 1000), {
      initialProps: { valor: "a" },
    });

    rerender({ valor: "b" });
    await vi.advanceTimersByTimeAsync(1000);

    expect(result.current).toBe("error");
  });
});

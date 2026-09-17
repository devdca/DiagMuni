import * as Sentry from "@sentry/react";
import type { Breadcrumb } from "@sentry/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { inicializarSentry } from "./sentry";

vi.mock("@sentry/react", () => ({ init: vi.fn() }));

describe("inicializarSentry", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.clearAllMocks();
  });

  it("no llama a Sentry.init si VITE_SENTRY_DSN no está configurada", () => {
    vi.stubEnv("VITE_SENTRY_DSN", "");
    inicializarSentry();
    expect(Sentry.init).not.toHaveBeenCalled();
  });

  it("llama a Sentry.init con el DSN cuando sí está configurada", () => {
    vi.stubEnv("VITE_SENTRY_DSN", "https://ejemplo@o0.ingest.sentry.io/1");
    inicializarSentry();
    expect(Sentry.init).toHaveBeenCalledTimes(1);
    expect(Sentry.init).toHaveBeenCalledWith(
      expect.objectContaining({ dsn: "https://ejemplo@o0.ingest.sentry.io/1", sendDefaultPii: false }),
    );
  });

  it("beforeBreadcrumb descarta datos sensibles de breadcrumbs fetch/xhr", () => {
    vi.stubEnv("VITE_SENTRY_DSN", "https://ejemplo@o0.ingest.sentry.io/1");
    inicializarSentry();
    const config = vi.mocked(Sentry.init).mock.calls[0][0];
    const breadcrumb: Breadcrumb = {
      category: "fetch",
      data: { input: "token-secreto", body: "form-data", Authorization: "Bearer xyz", url: "/api/x" },
    };
    const resultado = config?.beforeBreadcrumb?.(breadcrumb, {});
    expect(resultado?.data).not.toHaveProperty("input");
    expect(resultado?.data).not.toHaveProperty("body");
    expect(resultado?.data).not.toHaveProperty("Authorization");
    expect(resultado?.data).toHaveProperty("url", "/api/x");
  });
});

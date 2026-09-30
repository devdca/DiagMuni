// Extiende `expect` de Vitest con los matchers de jest-dom (toBeInTheDocument,
// toHaveTextContent, etc.) -- el subpath /vitest trae también los tipos, sin
// necesidad de agregar "vitest/globals" ni nada de jest-dom a tsconfig.json.
import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Testing Library limpia el DOM solo entre tests si detecta un test runner con
// globals activados -- este proyecto los evita a propósito (cada test importa
// describe/it/expect explícito, ver vite.config.ts), así que sin esto el
// render de un test se queda montado y contamina el siguiente (encontrado de
// verdad: un segundo test veía el DOM huérfano del primero en vez de su
// propio render).
afterEach(() => {
  cleanup();
});

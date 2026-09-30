// Ruta del storageState que escribe e2e/auth.setup.ts y consumen los specs.
// Vive en su propio módulo, sin `test()` ni `setup()`: playwright.config.ts la
// importa, y Playwright rechaza que la configuración importe un archivo que
// declare tests.
export const ARCHIVO_ESTADO_SESION = "e2e/.auth/estado.json";

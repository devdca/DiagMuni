// Credenciales del gobierno de prueba, inyectadas por variable de entorno --
// nunca un valor fijo en el repo: `bootstrap_tenant.py` genera la contraseña al
// vuelo y a propósito no acepta una fija (docs/plan-implementacion-alta-gobierno.md,
// sección 2 y 5). Quien corre los tests localmente crea su propio gobierno con
// `docker compose exec backend python -m app.bootstrap_tenant crear-gobierno ...`
// (docs/runbook-alta-gobierno.md) y exporta estas tres variables.

function requerida(nombre: string): string {
  const valor = process.env[nombre];
  if (!valor) {
    throw new Error(
      `Falta la variable de entorno ${nombre}. Crea un gobierno de prueba con ` +
        `docs/runbook-alta-gobierno.md y exporta E2E_CLAVE_GOBIERNO, E2E_EMAIL y E2E_PASSWORD.`,
    );
  }
  return valor;
}

export const credenciales = {
  get claveGobierno() {
    return requerida("E2E_CLAVE_GOBIERNO");
  },
  get email() {
    return requerida("E2E_EMAIL");
  },
  get password() {
    return requerida("E2E_PASSWORD");
  },
};

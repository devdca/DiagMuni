// Interruptor de tema claro/oscuro -- el mecanismo CSS (".dark" en <html>) ya
// existía, faltaba la UI para activarlo.
const CLAVE_TEMA = "diagmuni_tema";
export type Tema = "light" | "dark";

function prefiereOscuroDelSistema(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

// `null` si el funcionario nunca tocó el interruptor -- se sigue al sistema.
export function obtenerTemaGuardado(): Tema | null {
  const valor = localStorage.getItem(CLAVE_TEMA);
  return valor === "light" || valor === "dark" ? valor : null;
}

export function obtenerTemaActivo(): Tema {
  return obtenerTemaGuardado() ?? (prefiereOscuroDelSistema() ? "dark" : "light");
}

export function aplicarTema(tema: Tema): void {
  document.documentElement.classList.toggle("dark", tema === "dark");
}

export function fijarTema(tema: Tema): void {
  localStorage.setItem(CLAVE_TEMA, tema);
  aplicarTema(tema);
}

export function alternarTema(): Tema {
  const nuevo: Tema = obtenerTemaActivo() === "dark" ? "light" : "dark";
  fijarTema(nuevo);
  return nuevo;
}

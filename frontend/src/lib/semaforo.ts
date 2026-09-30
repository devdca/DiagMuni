// Paleta de estado del semáforo (docs/ux-brief.md, "Semáforo de seguimiento"),
// fija -- nunca reutilizada como color de serie. Variables CSS, no hex directo:
// "en_progreso"/"atrasado" no cumplen AA en ambos modos por diseño, por eso todo
// estado va siempre con ícono + etiqueta de texto, nunca solo el color.
export type EstadoSemaforo = "completado" | "en_progreso" | "atrasado";

export interface InfoEstadoSemaforo {
  etiqueta: string;
  hex: string;
  /** Decorativo (aria-hidden) -- el significado lo lleva `etiqueta`, no el ícono. */
  icono: string;
}

export const ESTADOS_SEMAFORO: Record<EstadoSemaforo, InfoEstadoSemaforo> = {
  completado: { etiqueta: "Completado", hex: "var(--semaforo-completado)", icono: "✓" },
  en_progreso: { etiqueta: "En progreso", hex: "var(--semaforo-en-progreso)", icono: "●" },
  atrasado: { etiqueta: "Atrasado o bloqueado", hex: "var(--semaforo-atrasado)", icono: "⚠" },
};

export const ORDEN_ESTADOS_SEMAFORO: readonly EstadoSemaforo[] = ["completado", "en_progreso", "atrasado"];

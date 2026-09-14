// Paleta de estado del semáforo de seguimiento (docs/ux-brief.md sección
// "Semáforo de seguimiento (F6)"), fija y validada -- nunca reutilizada como color
// de serie ni para otro propósito. Solo 3 estados, mismos valores que
// backend/app/models/accion_seguimiento.py::AccionSeguimiento.estado_semaforo.
//
// Variables CSS (frontend/src/index.css), no hex directo -- "completado" necesita
// un valor distinto por modo para cumplir AA 4.5:1 contra la tarjeta de cada uno
// (ver `frontend/scripts/validate_palette.js`). "en_progreso" y "atrasado" quedan
// como excepción documentada, mismo valor en ambos modos: caen bajo el piso de
// contraste 4.5:1 (y en algún caso 3:1) por diseño de la paleta -- por eso la
// regla dura de este documento: todo estado se muestra siempre con ícono +
// etiqueta de texto, nunca solo el punto de color.
export type EstadoSemaforo = "completado" | "en_progreso" | "atrasado";

export interface InfoEstadoSemaforo {
  etiqueta: string;
  hex: string;
  // Glyph decorativo (aria-hidden) -- el significado siempre lo lleva `etiqueta`,
  // nunca el ícono ni el color por sí solos.
  icono: string;
}

export const ESTADOS_SEMAFORO: Record<EstadoSemaforo, InfoEstadoSemaforo> = {
  completado: { etiqueta: "Completado", hex: "var(--semaforo-completado)", icono: "✓" },
  en_progreso: { etiqueta: "En progreso", hex: "var(--semaforo-en-progreso)", icono: "●" },
  atrasado: { etiqueta: "Atrasado o bloqueado", hex: "var(--semaforo-atrasado)", icono: "⚠" },
};

export const ORDEN_ESTADOS_SEMAFORO: readonly EstadoSemaforo[] = ["completado", "en_progreso", "atrasado"];

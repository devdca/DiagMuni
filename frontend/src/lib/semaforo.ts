// Paleta de estado del semáforo de seguimiento (docs/ux-brief.md sección
// "Semáforo de seguimiento (F6)"), fija y validada -- nunca reutilizada como color
// de serie ni para otro propósito. Solo 3 estados, mismos valores que
// backend/app/models/accion_seguimiento.py::AccionSeguimiento.estado_semaforo.
//
// Regla dura del documento: "warning" y "critical" caen bajo el piso de contraste
// 3:1 en superficie clara por diseño de la paleta -- todo estado debe mostrarse
// siempre con ícono + etiqueta de texto, nunca solo el punto de color.
export type EstadoSemaforo = "completado" | "en_progreso" | "atrasado";

export interface InfoEstadoSemaforo {
  etiqueta: string;
  hex: string;
  // Glyph decorativo (aria-hidden) -- el significado siempre lo lleva `etiqueta`,
  // nunca el ícono ni el color por sí solos.
  icono: string;
}

export const ESTADOS_SEMAFORO: Record<EstadoSemaforo, InfoEstadoSemaforo> = {
  completado: { etiqueta: "Completado", hex: "#0ca30c", icono: "✓" },
  en_progreso: { etiqueta: "En progreso", hex: "#fab219", icono: "●" },
  atrasado: { etiqueta: "Atrasado o bloqueado", hex: "#d03b3b", icono: "⚠" },
};

export const ORDEN_ESTADOS_SEMAFORO: readonly EstadoSemaforo[] = ["completado", "en_progreso", "atrasado"];

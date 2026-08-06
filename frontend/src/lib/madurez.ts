// Rampa ordinal del índice de madurez (0-4), docs/ux-brief.md sección "Índice de
// madurez (0-4) -- rampa ordinal, un solo hue, nunca semáforo de colores dispares".
// Hex tal cual el documento -- no se inventa ningún color acá. Solo se fija el paso
// de modo claro: el documento deja el modo oscuro pendiente de una revalidación con
// `scripts/validate_palette.js --mode dark --ordinal` que no es parte de esta tarea.
export interface NivelMadurez {
  nivel: 0 | 1 | 2 | 3 | 4;
  etiqueta: string;
  hexClaro: string;
}

export const NIVELES_MADUREZ: readonly NivelMadurez[] = [
  { nivel: 0, etiqueta: "Presencial en papel", hexClaro: "#86b6ef" },
  { nivel: 1, etiqueta: "Informativo", hexClaro: "#5598e7" },
  { nivel: 2, etiqueta: "Transaccional parcial", hexClaro: "#2a78d6" },
  { nivel: 3, etiqueta: "Transaccional completo", hexClaro: "#1c5cab" },
  { nivel: 4, etiqueta: "Proactivo e interoperable", hexClaro: "#104281" },
];

export function obtenerNivelMadurez(indice: number): NivelMadurez {
  // El índice global es un promedio (backend/app/engine/madurez.py,
  // calcular_indice_global) y puede no ser entero -- se redondea solo para elegir
  // a qué nivel de la rampa corresponde el color y la etiqueta; la cifra grande
  // de la tarjeta muestra el promedio real, sin redondear (ver PanelResumen.tsx).
  const nivelRedondeado = Math.min(4, Math.max(0, Math.round(indice))) as NivelMadurez["nivel"];
  return NIVELES_MADUREZ[nivelRedondeado];
}

// Rampa ordinal del índice (0-4), un solo hue -- nunca semáforo de colores dispares
// (docs/ux-brief.md, "Índice de madurez"). Dos variantes, nunca intercambiables:
// hexClaro es solo decorativo (piso 2:1, no usar en texto/borde); varTexto es
// AA 4.5:1 y theme-aware para cuando el nivel se pinta como texto/borde.
export interface NivelMadurez {
  nivel: 0 | 1 | 2 | 3 | 4;
  etiqueta: string;
  hexClaro: string;
  varTexto: string;
  /** Para superficies siempre oscuras (hero de Panel resumen) -- no usar varTexto ahí. */
  varTextoSobreOscuro: string;
}

export const NIVELES_MADUREZ: readonly NivelMadurez[] = [
  {
    nivel: 0,
    etiqueta: "Presencial en papel",
    hexClaro: "#9ea8e5",
    varTexto: "var(--madurez-nivel-0-texto)",
    varTextoSobreOscuro: "var(--madurez-nivel-0-texto-sobre-oscuro)",
  },
  {
    nivel: 1,
    etiqueta: "Informativo",
    hexClaro: "#8f9be3",
    varTexto: "var(--madurez-nivel-1-texto)",
    varTextoSobreOscuro: "var(--madurez-nivel-1-texto-sobre-oscuro)",
  },
  {
    nivel: 2,
    etiqueta: "Transaccional parcial",
    hexClaro: "#6674d6",
    varTexto: "var(--madurez-nivel-2-texto)",
    varTextoSobreOscuro: "var(--madurez-nivel-2-texto-sobre-oscuro)",
  },
  {
    nivel: 3,
    etiqueta: "Transaccional completo",
    hexClaro: "#4152c4",
    varTexto: "var(--madurez-nivel-3-texto)",
    varTextoSobreOscuro: "var(--madurez-nivel-3-texto-sobre-oscuro)",
  },
  {
    nivel: 4,
    etiqueta: "Proactivo e interoperable",
    hexClaro: "#28349e",
    varTexto: "var(--madurez-nivel-4-texto)",
    varTextoSobreOscuro: "var(--madurez-nivel-4-texto-sobre-oscuro)",
  },
];

export function obtenerNivelMadurez(indice: number): NivelMadurez {
  // El promedio puede no ser entero -- se redondea solo para el color/etiqueta;
  // la cifra grande muestra el promedio real sin redondear (ver PanelResumen.tsx).
  const nivelRedondeado = Math.min(4, Math.max(0, Math.round(indice))) as NivelMadurez["nivel"];
  return NIVELES_MADUREZ[nivelRedondeado];
}

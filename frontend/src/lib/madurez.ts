// Rampa ordinal del índice de madurez (0-4), docs/ux-brief.md sección "Índice de
// madurez (0-4) -- rampa ordinal, un solo hue, nunca semáforo de colores dispares".
//
// Dos usos, dos colores -- nunca el mismo hex para ambos:
// - hexClaro: SOLO decorativo (ej. el punto aria-hidden junto al Badge). Cumple
//   apenas el piso de contraste 2:1 que el brief acepta para uso ordinal -- si se
//   usa como color de texto o de borde puede incumplir AA en algunos niveles (ver
//   `frontend/scripts/validate_palette.js --ordinal`).
// - varTexto: variable CSS (frontend/src/index.css) con el color AA-safe (4.5:1
//   contra --card y --background) para cuando el nivel se pinta como texto o
//   borde -- cifra grande del índice, borde/texto del Badge de índice. Theme-aware
//   por sí sola (valores distintos bajo `.dark`), revalidada para modo oscuro
//   (reutilizar hexClaro tal cual en oscuro rompía AA -- ver
//   `validate_palette.js --mode dark --ordinal`).
export interface NivelMadurez {
  nivel: 0 | 1 | 2 | 3 | 4;
  etiqueta: string;
  hexClaro: string;
  varTexto: string;
}

export const NIVELES_MADUREZ: readonly NivelMadurez[] = [
  { nivel: 0, etiqueta: "Presencial en papel", hexClaro: "#9ea8e5", varTexto: "var(--madurez-nivel-0-texto)" },
  { nivel: 1, etiqueta: "Informativo", hexClaro: "#8f9be3", varTexto: "var(--madurez-nivel-1-texto)" },
  { nivel: 2, etiqueta: "Transaccional parcial", hexClaro: "#6674d6", varTexto: "var(--madurez-nivel-2-texto)" },
  { nivel: 3, etiqueta: "Transaccional completo", hexClaro: "#4152c4", varTexto: "var(--madurez-nivel-3-texto)" },
  { nivel: 4, etiqueta: "Proactivo e interoperable", hexClaro: "#28349e", varTexto: "var(--madurez-nivel-4-texto)" },
];

export function obtenerNivelMadurez(indice: number): NivelMadurez {
  // El índice global es un promedio (backend/app/engine/madurez.py,
  // calcular_indice_global) y puede no ser entero -- se redondea solo para elegir
  // a qué nivel de la rampa corresponde el color y la etiqueta; la cifra grande
  // de la tarjeta muestra el promedio real, sin redondear (ver PanelResumen.tsx).
  const nivelRedondeado = Math.min(4, Math.max(0, Math.round(indice))) as NivelMadurez["nivel"];
  return NIVELES_MADUREZ[nivelRedondeado];
}

#!/usr/bin/env node
// Valida contraste WCAG 2.1 AA de la paleta de DiagMuni. Fuente de verdad de los
// valores hex: deben coincidir con frontend/src/index.css (paleta base) y
// frontend/src/lib/madurez.ts / lib/semaforo.ts (rampas) -- docs/ux-brief.md
// documenta estos mismos valores, no al revés (ver docs/ux-brief.md, "Paleta").
//
// Uso:
//   node scripts/validate_palette.js                    valida todo (base + rampas), ambos modos
//   node scripts/validate_palette.js --mode dark         solo modo oscuro
//   node scripts/validate_palette.js --mode light        solo modo claro
//   node scripts/validate_palette.js --ordinal           solo la rampa de madurez (0-4)
//
// Exit code 1 si algún par no exento incumple su umbral -- pensado para correrse
// a mano cada vez que se toque una de estas tres fuentes, no wireado a CI todavía.

const args = process.argv.slice(2);
const modeArg = args.includes("--mode") ? args[args.indexOf("--mode") + 1] : "all";
const onlyOrdinal = args.includes("--ordinal");
const modes = modeArg === "all" ? ["light", "dark"] : [modeArg];

function hexToRgb(hex) {
  const n = parseInt(hex.replace("#", ""), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function relativeLuminance([r, g, b]) {
  const channel = (c) => {
    c /= 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  };
  const [R, G, B] = [channel(r), channel(g), channel(b)];
  return 0.2126 * R + 0.7152 * G + 0.0722 * B;
}

function contrast(hexA, hexB) {
  const lA = relativeLuminance(hexToRgb(hexA));
  const lB = relativeLuminance(hexToRgb(hexB));
  const lighter = Math.max(lA, lB);
  const darker = Math.min(lA, lB);
  return (lighter + 0.05) / (darker + 0.05);
}

// Paleta base -- frontend/src/index.css, bloques :root (light) y .dark.
// "Tinta neutra": reemplaza "Índigo confiado" tras feedback de que ese índigo,
// repetido en nav/botones/foco Y en la rampa del índice a la vez, se leía "todo
// azul" -- ver docs/ux-brief.md, sección "Paleta". Ahora la acción/navegación es
// tinta casi-negra (casi-blanca en oscuro) y el azul de la rampa (sin tocar)
// queda como el único color con significado propio de toda la interfaz.
// Sistema "Fría/técnica" (docs/design-system.md) -- reemplaza "Tinta neutra".
const BASE = {
  light: {
    background: "#fafafa",
    card: "#ffffff",
    foreground: "#171717",
    mutedForeground: "#5c5f66",
    atenuado: "#6b6e75",
    border: "#8c8c90",
    primary: "#171717",
    primaryForeground: "#fafafa",
    destructive: "#ad2a24",
    destructiveForeground: "#fff5f4",
  },
  dark: {
    background: "#0a0a0c",
    card: "#131316",
    foreground: "#f2f2f3",
    mutedForeground: "#a8acb8",
    atenuado: "#8b8e96",
    border: "#606067",
    primary: "#f2f2f3",
    primaryForeground: "#0a0a0c",
    destructive: "#e8635c",
    destructiveForeground: "#280604",
  },
};

// 4 roles de estado con nombre propio (docs/design-system.md, sección 2) --
// "exito"/"critico" reutilizan los mismos hex del semáforo (incluidos abajo,
// no un valor nuevo); "alerta"/"info" son nuevos, reemplazan los admonition
// boxes que usaban amber-500/emerald-500 de Tailwind sin editar.
const ESTADOS = {
  light: { exito: "#0d770d", alerta: "#92620a", critico: "#ad2a24", info: "#33578a" },
  dark: { exito: "#4dcb4d", alerta: "#e0a83e", critico: "#e8635c", info: "#7fa6d9" },
};

// Pares de texto normal (< 24px o < 19px bold) -- umbral AA 4.5:1.
const BASE_TEXT_PAIRS = [
  ["foreground", "background", "Texto primario / superficie de página"],
  ["foreground", "card", "Texto primario / superficie de tarjeta"],
  ["mutedForeground", "background", "Texto secundario / superficie de página"],
  ["mutedForeground", "card", "Texto secundario / superficie de tarjeta"],
  ["atenuado", "background", "Texto atenuado (ayudas/placeholders) / superficie de página"],
  ["atenuado", "card", "Texto atenuado (ayudas/placeholders) / superficie de tarjeta"],
  ["primaryForeground", "primary", "Texto de botón primario / fondo primario"],
  ["destructiveForeground", "destructive", "Texto de botón destructivo / fondo destructivo"],
];

// Borde contra la superficie que lo rodea -- umbral AA no-texto 3:1 (WCAG 1.4.11).
const BASE_NONTEXT_PAIRS = [["border", "background", "Línea divisoria / superficie de página"]];

// Rampa ordinal de madurez (0-4) -- frontend/src/lib/madurez.ts.
// hexClaro: SOLO decorativo (swatch aria-hidden) -- piso 2:1 aceptado a propósito,
// nunca se usa como color de texto ni de borde (docs/ux-brief.md, "Índice de madurez").
const MADUREZ_CLARO = ["#9ea8e5", "#8f9be3", "#6674d6", "#4152c4", "#28349e"];

// varTexto -- color AA-safe (4.5:1) para cuando el nivel se pinta como texto o
// borde (cifra grande, borde/texto del Badge de índice). Theme-aware: valores
// distintos por modo, ambos verificados contra card Y background de ese modo.
const MADUREZ_TEXTO = {
  light: ["#2d3ea9", "#253393", "#1c297d", "#141e61", "#0b1341"],
  dark: ["#cad0f6", "#b1baf1", "#98a3eb", "#808de5", "#7583e1"],
};

// Semáforo de seguimiento (F6) -- frontend/src/lib/semaforo.ts. Theme-aware:
// "completado" tiene valor propio por modo (necesario para AA 4.5:1 contra la
// tarjeta de cada uno); "en_progreso"/"atrasado" son el mismo hex en ambos modos
// y caen bajo AA a propósito (documentado en docs/ux-brief.md) -- siempre van con
// ícono + etiqueta, así que se reportan pero nunca hacen fallar el exit code.
const SEMAFORO = {
  light: { completado: "#0d770d", en_progreso: "#fab219", atrasado: "#d03b3b" },
  dark: { completado: "#4dcb4d", en_progreso: "#fab219", atrasado: "#d03b3b" },
};
const SEMAFORO_EXENTO_AA = new Set(["en_progreso", "atrasado"]);

// Franja "hero" del índice global (Panel resumen) -- frontend/src/index.css,
// identidad fija en claro/oscuro (mismo criterio que el navbar, ninguno de
// los dos hereda de BASE/.dark). docs/ux-brief.md, "Revisión de diseño --
// ronda 2". Se valida una sola vez, no por modo -- esta superficie no cambia
// con el tema de la página.
const HERO = {
  bg: "#161614",
  foreground: "#f5f4f0",
  foregroundMuted: "#c7c5be",
};

// Mismos 5 hex que MADUREZ_TEXTO.dark -- variante "sobre oscuro" de la
// rampa, para pintar la cifra del índice sobre --hero-bg
// (frontend/src/lib/madurez.ts, campo `varTextoSobreOscuro`). Si
// MADUREZ_TEXTO.dark cambia, actualizar también esto.
const MADUREZ_SOBRE_OSCURO = MADUREZ_TEXTO.dark;

let anyFail = false;

function report(label, ratio, threshold, exempt = false) {
  const pass = ratio >= threshold;
  if (!pass && !exempt) anyFail = true;
  const mark = pass ? "OK  " : exempt ? "!!  " : "FAIL";
  const note = exempt && !pass ? "  (excepción documentada, requiere ícono+etiqueta)" : "";
  console.log(`  [${mark}] ${label}: ${ratio.toFixed(2)}:1 (mínimo ${threshold}:1)${note}`);
}

for (const mode of modes) {
  console.log(`\n== Modo ${mode} ==`);
  const base = BASE[mode];

  if (!onlyOrdinal) {
    console.log(" Paleta base -- texto (AA 4.5:1):");
    for (const [fg, bg, label] of BASE_TEXT_PAIRS) {
      report(label, contrast(base[fg], base[bg]), 4.5);
    }
    console.log(" Paleta base -- no-texto / bordes (AA 3:1):");
    for (const [fg, bg, label] of BASE_NONTEXT_PAIRS) {
      report(label, contrast(base[fg], base[bg]), 3);
    }
    console.log(" Semáforo de seguimiento:");
    for (const [estado, hex] of Object.entries(SEMAFORO[mode])) {
      report(`${estado} / superficie de tarjeta`, contrast(hex, base.card), 4.5, SEMAFORO_EXENTO_AA.has(estado));
    }
    console.log(" Roles de estado (avisos, docs/design-system.md):");
    for (const [rol, hex] of Object.entries(ESTADOS[mode])) {
      report(`${rol} / superficie de tarjeta`, contrast(hex, base.card), 4.5);
      report(`${rol} / superficie de página`, contrast(hex, base.background), 4.5);
    }
  }

  console.log(" Rampa ordinal de madurez -- hexClaro (decorativo, piso 2:1, nunca texto/borde):");
  MADUREZ_CLARO.forEach((hex, nivel) => {
    report(`nivel ${nivel} / superficie de tarjeta`, contrast(hex, base.card), 2, true);
  });

  console.log(" Rampa ordinal de madurez -- varTexto (AA 4.5:1, uso como texto/borde):");
  MADUREZ_TEXTO[mode].forEach((hex, nivel) => {
    report(`nivel ${nivel} / superficie de tarjeta`, contrast(hex, base.card), 4.5);
    report(`nivel ${nivel} / superficie de página`, contrast(hex, base.background), 4.5);
  });
}

if (!onlyOrdinal) {
  console.log("\n== Franja hero (superficie fija, Panel resumen) ==");
  report("Texto / fondo hero", contrast(HERO.foreground, HERO.bg), 4.5);
  report("Texto atenuado / fondo hero", contrast(HERO.foregroundMuted, HERO.bg), 4.5);
}
console.log(" Rampa ordinal -- texto sobre oscuro (AA 4.5:1 contra --hero-bg):");
MADUREZ_SOBRE_OSCURO.forEach((hex, nivel) => {
  report(`nivel ${nivel} / franja hero`, contrast(hex, HERO.bg), 4.5);
});

console.log();
if (anyFail) {
  console.error("Resultado: hay pares que incumplen su umbral AA. Ver [FAIL] arriba.");
  process.exit(1);
} else {
  console.log("Resultado: toda la paleta (salvo excepciones documentadas del semáforo) cumple WCAG 2.1 AA.");
}

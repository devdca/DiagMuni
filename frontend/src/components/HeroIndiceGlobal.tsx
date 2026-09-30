import { obtenerNivelMadurez } from "@/lib/madurez";
import { useLogoGobiernoUrl } from "@/lib/useLogoGobierno";

// Franja "hero" del índice global -- superficie siempre oscura (--hero-bg)
// con el logo como marca de agua en escala de grises: a color competiría con
// el único azul con significado de la app (la rampa de madurez).

const ALTO_SPARK = 40;
const ANCHO_SPARK = 160;
const INDICE_MIN = 0;
const INDICE_MAX = 4;

function construirPuntosSpark(puntos: { indice_global: number }[]): string {
  const ultimos = puntos.slice(-6);
  const paso = ultimos.length > 1 ? ANCHO_SPARK / (ultimos.length - 1) : 0;
  return ultimos
    .map((p, i) => {
      const x = i * paso;
      const fraccion = (p.indice_global - INDICE_MIN) / (INDICE_MAX - INDICE_MIN);
      const y = ALTO_SPARK - Math.max(0, Math.min(1, fraccion)) * ALTO_SPARK;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

function CifraIndice({
  indiceGlobal,
  delta,
  puntosSpark,
}: {
  indiceGlobal: number;
  delta: number | null;
  puntosSpark: string | null;
}) {
  const nivel = obtenerNivelMadurez(indiceGlobal);

  return (
    <>
      <div className="mt-2 flex flex-wrap items-end gap-4">
        <span
          className="hero-indice-cifra text-6xl font-extrabold tracking-tight tabular-nums md:text-7xl"
          style={{ color: nivel.varTextoSobreOscuro }}
        >
          {indiceGlobal.toFixed(1)}
        </span>
        <span className="pb-1 text-lg font-medium" style={{ color: "var(--hero-foreground-muted)" }}>
          {nivel.etiqueta}
        </span>
      </div>

      {puntosSpark && (
        <svg
          aria-hidden
          viewBox={`0 0 ${ANCHO_SPARK} ${ALTO_SPARK}`}
          width={ANCHO_SPARK}
          height={ALTO_SPARK}
          className="mt-4"
        >
          <polyline
            className="hero-spark-linea"
            points={puntosSpark}
            fill="none"
            stroke={nivel.varTextoSobreOscuro}
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}

      {delta !== null && (
        <p className="mt-3 text-sm font-semibold" style={{ color: "var(--hero-foreground-muted)" }}>
          {delta >= 0 ? "↗" : "↘"} {delta >= 0 ? "+" : ""}
          {delta.toFixed(1)} vs. hace 3 meses
        </p>
      )}
    </>
  );
}

export function HeroIndiceGlobal({
  pais,
  indiceGlobal,
  delta,
  fechaUltimoDiagnostico,
  historial,
}: {
  pais: string;
  indiceGlobal: number | null;
  delta: number | null;
  fechaUltimoDiagnostico: string | null;
  historial: { indice_global: number; creado_en: string }[];
}) {
  const puntosSpark = historial.length >= 2 ? construirPuntosSpark(historial) : null;
  const logoUrl = useLogoGobiernoUrl();

  return (
    <div
      className="shadow-hero relative overflow-hidden rounded-2xl p-8 md:p-10"
      style={{ background: "var(--hero-bg)", color: "var(--hero-foreground)" }}
    >
      {/* Marca de agua decorativa -- sin logo (404), la franja se queda como antes. */}
      {logoUrl && (
        <img
          aria-hidden
          src={logoUrl}
          alt=""
          className="absolute top-1/2 right-0 h-[140%] w-auto -translate-y-1/2 opacity-[0.14] grayscale"
          style={{ maskImage: "linear-gradient(to left, black 40%, transparent 90%)" }}
        />
      )}

      <div className="relative">
        <p
          className="text-xs font-bold tracking-[0.14em] uppercase"
          style={{ color: "var(--hero-foreground-muted)" }}
        >
          {pais}
        </p>

        {indiceGlobal === null ? (
          <p className="mt-3 text-sm" style={{ color: "var(--hero-foreground-muted)" }}>
            Todavía no hay ningún trámite diagnosticado.
          </p>
        ) : (
          <CifraIndice indiceGlobal={indiceGlobal} delta={delta} puntosSpark={puntosSpark} />
        )}

        <p className="mt-5 text-xs" style={{ color: "var(--hero-foreground-muted)" }}>
          {fechaUltimoDiagnostico
            ? `Último diagnóstico: ${new Date(fechaUltimoDiagnostico).toLocaleDateString("es", { year: "numeric", month: "long", day: "numeric" })}`
            : "Aún no hay ningún diagnóstico completado"}
        </p>
      </div>
    </div>
  );
}

import { useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts/core";
import { GridComponent, LegendComponent, ToolboxComponent, TooltipComponent } from "echarts/components";
import { LineChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import type { ComposeOption } from "echarts/core";
import type {
  GridComponentOption,
  LegendComponentOption,
  ToolboxComponentOption,
  TooltipComponentOption,
} from "echarts/components";
import type { LineSeriesOption } from "echarts/charts";

import { resolverColorCss } from "@/lib/colorCss";
import { obtenerHistorialIndiceGlobal, type PuntoIndiceGlobalResponse } from "@/lib/tramitesApi";
import { NIVELES_MADUREZ } from "@/lib/madurez";

// Distribución de trámites activos por nivel de madurez, apilada en el
// tiempo, con datos reales (nunca series inventadas). El promedio se muestra
// aparte como cifra grande (PanelResumen.tsx); esto cuenta la historia detrás.
// Solo se registran los módulos que se usan, no el paquete completo de echarts.
echarts.use([GridComponent, LegendComponent, ToolboxComponent, TooltipComponent, LineChart, CanvasRenderer]);

type OpcionGrafica = ComposeOption<
  GridComponentOption | LegendComponentOption | ToolboxComponentOption | TooltipComponentOption | LineSeriesOption
>;

// Una clave por nivel, en el mismo orden que NIVELES_MADUREZ -- evita repetir
// un switch/if por nivel al armar cada serie.
const CLAVE_CONTEO_POR_NIVEL = [
  "nivel_0_conteo",
  "nivel_1_conteo",
  "nivel_2_conteo",
  "nivel_3_conteo",
  "nivel_4_conteo",
] as const satisfies readonly (keyof PuntoIndiceGlobalResponse)[];

// `refetchInterval` (no un stream) -- para que otro funcionario viendo el
// panel vea el punto nuevo sin recargar.
const REFRESCO_MS = 30_000;

// Referencia estable: un `?? []` literal crearía un arreglo nuevo en cada
// render y rompería la memoización de `useMemo` de abajo.
const SIN_PUNTOS: PuntoIndiceGlobalResponse[] = [];

// Paleta LOCAL, distinta de NIVELES_MADUREZ.hexClaro (que es "un solo hue" en
// el resto del producto) -- pedido puntual de "estilo semáforo sin rojo" para
// esta gráfica. Validada con validate_palette.js (CVD OK; el ámbar queda bajo
// 3:1, aceptado porque el nivel también se identifica por leyenda/tooltip/eje).
const COLOR_BANDA_POR_NIVEL = [
  "#c2410c", // nivel 0 -- peor: naranja profundo, nunca rojo
  "#ca8a04", // nivel 1 -- ámbar
  "#4338ca", // nivel 2 -- indigo (mismo hue de marca que el resto del producto)
  "#0891b2", // nivel 3 -- cian/teal
  "#16a34a", // nivel 4 -- mejor: verde
] as const;

// Degradado vertical: solo varía la opacidad del hex de arriba, nunca un
// segundo tono inventado.
function hexConAlpha(hex: string, alpha: number): string {
  const numero = Number.parseInt(hex.slice(1), 16);
  const r = (numero >> 16) & 255;
  const g = (numero >> 8) & 255;
  const b = numero & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function formatearFechaCorta(fechaIso: string): string {
  return new Date(fechaIso).toLocaleDateString("es", { day: "numeric", month: "short" });
}

function formatearFechaHora(fechaIso: string): string {
  return new Date(fechaIso).toLocaleString("es", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

const NOMBRE_SERIE_INDICE = "Índice de madurez global";

function construirOpcion(puntos: PuntoIndiceGlobalResponse[]): OpcionGrafica {
  const colorBorde = resolverColorCss("var(--border)");
  const colorTexto = resolverColorCss("var(--atenuado)");
  const colorTarjeta = resolverColorCss("var(--card)");
  const colorTextoTarjeta = resolverColorCss("var(--card-foreground)");
  const colorIndice = resolverColorCss("var(--foreground)");

  // Una serie por nivel de la rampa (0-4), apiladas.
  const seriesNiveles: LineSeriesOption[] = NIVELES_MADUREZ.map((nivel, i) => ({
    name: `${nivel.nivel} — ${nivel.etiqueta}`,
    type: "line",
    stack: "total",
    smooth: true,
    showSymbol: false,
    lineStyle: { width: 0 },
    areaStyle: {
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: hexConAlpha(COLOR_BANDA_POR_NIVEL[i], 0.85) },
        { offset: 1, color: hexConAlpha(COLOR_BANDA_POR_NIVEL[i], 0.35) },
      ]),
    },
    emphasis: { focus: "series" },
    yAxisIndex: 0,
    data: puntos.map((p) => p[CLAVE_CONTEO_POR_NIVEL[i]]),
  }));

  // El índice real se dibuja encima de las áreas apiladas (que solo muestran
  // conteo de trámites, no el índice), en su propio eje y en tinta neutra
  // para leerse como "la cifra", no como un nivel más. `z` alto para no quedar tapado.
  const serieIndice: LineSeriesOption = {
    name: NOMBRE_SERIE_INDICE,
    type: "line",
    yAxisIndex: 1,
    smooth: true,
    showSymbol: true,
    symbolSize: 6,
    z: 10,
    lineStyle: { width: 3, color: colorIndice },
    itemStyle: { color: colorIndice },
    data: puntos.map((p) => p.indice_global),
  };

  return {
    color: [...COLOR_BANDA_POR_NIVEL, colorIndice],
    legend: {
      bottom: 0,
      itemWidth: 12,
      itemHeight: 12,
      textStyle: { color: colorTexto, fontSize: 11 },
    },
    toolbox: {
      right: 8,
      top: 0,
      feature: { saveAsImage: { title: "Guardar imagen" } },
      iconStyle: { borderColor: colorTexto },
      emphasis: { iconStyle: { borderColor: colorIndice } },
    },
    grid: { left: 40, right: 40, top: 16, bottom: 56 },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: puntos.map((p) => formatearFechaCorta(p.creado_en)),
      axisLine: { lineStyle: { color: colorBorde } },
      axisLabel: { color: colorTexto, fontSize: 11 },
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: "value",
        name: "Trámites",
        nameTextStyle: { color: colorTexto, fontSize: 10 },
        // Sin rango fijo -- esto cuenta trámites, y ese total crece.
        minInterval: 1,
        splitLine: { show: false },
        axisLabel: { color: colorTexto, fontSize: 11 },
        axisLine: { show: false },
      },
      {
        type: "value",
        name: "Índice",
        nameTextStyle: { color: colorTexto, fontSize: 10 },
        // Rango fijo 0-4, no el mínimo/máximo de los datos -- escala consistente.
        min: 0,
        max: 4,
        interval: 1,
        splitLine: { show: false },
        axisLabel: { color: colorIndice, fontSize: 11 },
        axisLine: { show: true, lineStyle: { color: colorIndice } },
      },
    ],
    tooltip: {
      trigger: "axis",
      backgroundColor: colorTarjeta,
      borderColor: colorBorde,
      textStyle: { color: colorTextoTarjeta },
      formatter: (parametros) => {
        const lista = Array.isArray(parametros) ? parametros : [parametros];
        if (lista.length === 0) return "";
        const indiceDato = lista[0].dataIndex ?? 0;
        const fecha = formatearFechaHora(puntos[indiceDato].creado_en);
        // Delta vs. el punto anterior -- `lista` llega en el mismo orden que
        // `series`, se usa esa posición para ir a buscar el valor previo.
        const anterior = indiceDato > 0 ? puntos[indiceDato - 1] : null;
        const filas = lista.map((p, i) => {
          const marcador = typeof p.marker === "string" ? p.marker : "";
          const esIndice = p.seriesName === NOMBRE_SERIE_INDICE;
          const numero = typeof p.value === "number" ? p.value : Number(p.value);
          const valor = esIndice ? numero.toFixed(1) : String(numero);
          let delta = "";
          if (anterior) {
            const numeroAnterior = esIndice ? anterior.indice_global : anterior[CLAVE_CONTEO_POR_NIVEL[i]];
            const diferencia = numero - numeroAnterior;
            if (diferencia !== 0) {
              const signo = diferencia > 0 ? "+" : "";
              const texto = esIndice ? diferencia.toFixed(1) : String(diferencia);
              delta = ` <span style="opacity:0.7;">(${signo}${texto})</span>`;
            }
          }
          return `${marcador} ${p.seriesName}: <strong>${valor}</strong>${delta}`;
        });
        return [fecha, ...filas].join("<br/>");
      },
    },
    animationDuration: 700,
    animationEasing: "cubicOut",
    series: [...seriesNiveles, serieIndice],
  };
}

export function GraficaTendenciaIndice() {
  const historialQuery = useQuery({
    queryKey: ["historial-indice-global"],
    queryFn: obtenerHistorialIndiceGlobal,
    refetchInterval: REFRESCO_MS,
  });

  const puntos = historialQuery.data ?? SIN_PUNTOS;
  // Con 0-1 puntos no hay "tendencia" real que mostrar.
  const opcion = useMemo(() => (puntos.length >= 2 ? construirOpcion(puntos) : null), [puntos]);

  const contenedorRef = useRef<HTMLDivElement>(null);
  const graficaRef = useRef<echarts.ECharts | null>(null);

  // Inicialización perezosa: un efecto de montaje con deps `[]` corría antes
  // de que el <div ref={contenedorRef}> existiera (mientras cargaba o había
  // <2 puntos) y nunca volvía a correr -- `echarts.init` nunca se llamaba. Este
  // efecto reacciona a `opcion`, así que corre de nuevo cuando hay datos reales.
  useEffect(() => {
    if (!contenedorRef.current || !opcion) return;
    if (graficaRef.current && graficaRef.current.getDom() !== contenedorRef.current) {
      graficaRef.current.dispose();
      graficaRef.current = null;
    }
    if (!graficaRef.current) {
      graficaRef.current = echarts.init(contenedorRef.current);
    }
    graficaRef.current.setOption(opcion, true);
  }, [opcion]);

  // Solo limpieza: listener de resize y liberar la instancia al desmontar.
  useEffect(() => {
    const alRedimensionar = () => graficaRef.current?.resize();
    window.addEventListener("resize", alRedimensionar);
    return () => {
      window.removeEventListener("resize", alRedimensionar);
      graficaRef.current?.dispose();
      graficaRef.current = null;
    };
  }, []);

  if (historialQuery.isLoading) {
    return <p className="text-sm text-atenuado">Cargando tendencia...</p>;
  }
  if (historialQuery.isError) {
    return <p className="text-sm text-destructive">No se pudo cargar la tendencia del índice.</p>;
  }
  if (puntos.length < 2) {
    // Ilustración estática que acompaña el texto, nunca lo reemplaza.
    return (
      <div className="flex flex-col items-center gap-3 py-6 text-center">
        <svg
          aria-hidden
          width="40"
          height="40"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--border)"
          strokeWidth="1.5"
          strokeLinecap="round"
        >
          <path d="M4 20h16" />
          <circle cx="8" cy="15" r="1.4" fill="var(--border)" stroke="none" />
          <circle cx="13" cy="12" r="1.4" fill="var(--border)" stroke="none" />
          <circle cx="18" cy="8" r="1.4" fill="var(--border)" stroke="none" />
          <path d="M8 15l5-3 5-4" strokeDasharray="2 3" />
        </svg>
        <p className="text-sm text-atenuado">
          Todavía no hay suficientes diagnósticos enviados para mostrar una tendencia (se necesitan al menos 2).
        </p>
      </div>
    );
  }

  const ultimo = puntos[puntos.length - 1];

  return (
    <div className="flex flex-col gap-2">
      <div ref={contenedorRef} style={{ width: "100%", height: 200 }} />
      <p className="text-xs text-atenuado">
        {puntos.length} {puntos.length === 1 ? "diagnóstico enviado" : "diagnósticos enviados"} · último:{" "}
        {formatearFechaHora(ultimo.creado_en)}
      </p>
    </div>
  );
}

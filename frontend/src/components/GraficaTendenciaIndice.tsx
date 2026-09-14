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

// Gráfica de tendencia -- distribución de trámites activos por nivel de
// madurez (0-4), apilada en el tiempo (pedido explícito: que se vea como un
// "gradient stacked area chart", pero con datos reales -- cuántos trámites
// hay en cada nivel de la rampa en cada momento, nunca series inventadas).
// Antes era una sola línea con el promedio; el promedio se sigue mostrando
// como cifra grande en la tarjeta de arriba (PanelResumen.tsx), esta gráfica
// ahora cuenta la historia completa detrás de ese promedio.
//
// ECharts en vez del SVG hecho a mano de antes (pedido explícito: tooltip
// real al pasar el mouse y exportar como imagen). Solo se registran los
// módulos que realmente se usan (line + grid + tooltip + leyenda + canvas),
// no el paquete completo de echarts -- mismo criterio de "instalar solo lo
// que la tarea necesita" que el resto del kit de UI (ver button.tsx, tabs.tsx).
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

// Datos REALES de backend/app/aplicacion/historial_indice_global.py (migración
// 0015), nunca simulados: cada punto es el índice global recalculado en el
// momento exacto de un envío/corrección de diagnóstico real. `refetchInterval`
// (no un stream) para que un segundo funcionario viendo el panel al mismo
// tiempo vea el punto nuevo sin recargar -- "tiempo real" en el sentido de
// "refleja la base de datos", no de "se mueve solo".
const REFRESCO_MS = 30_000;

// Referencia estable para cuando `historialQuery.data` todavía es `undefined`
// -- un `?? []` literal crearía un arreglo nuevo en cada render y rompería la
// memoización de `useMemo` de abajo (warning de react-hooks/exhaustive-deps).
const SIN_PUNTOS: PuntoIndiceGlobalResponse[] = [];

// Paleta LOCAL de esta gráfica, distinta de NIVELES_MADUREZ.hexClaro -- pedido
// explícito del usuario ("estilo semáforo, sin rojo" para las bandas de ESTA
// gráfica). docs/ux-brief.md fija la rampa de madurez como "un solo hue, nunca
// semáforo de colores dispares" para texto/badges del índice en el resto del
// producto (ver madurez.ts) -- esa regla sigue vigente ahí; esta paleta vive
// aislada acá para no romperla en ningún otro lugar, ya que el pedido fue
// puntual a esta visualización.
//
// Validada con dataviz/scripts/validate_palette.js (categorical, modo light,
// superficie #fcfcfb): separación CVD y piso de visión normal OK en los 5
// colores; único WARN es contraste del ámbar contra la superficie (2.86:1,
// bajo 3:1) -- igual que la excepción ya documentada de "en_progreso" en
// semaforo.ts, cubierta porque el nivel siempre se identifica también por
// leyenda/tooltip/eje, nunca solo por el color del área.
const COLOR_BANDA_POR_NIVEL = [
  "#c2410c", // nivel 0 -- peor: naranja profundo, nunca rojo
  "#ca8a04", // nivel 1 -- ámbar
  "#4338ca", // nivel 2 -- indigo (mismo hue de marca que el resto del producto)
  "#0891b2", // nivel 3 -- cian/teal
  "#16a34a", // nivel 4 -- mejor: verde
] as const;

// Para el degradado vertical de cada banda (pedido explícito: que se vea como
// el ejemplo oficial "Gradient Stacked Area Chart" de ECharts) solo se varía
// la opacidad del mismo hex de arriba, nunca un segundo tono inventado a mano
// por nivel. Piso subido de 0.15 a 0.35 (antes el borde inferior del área casi
// se perdía contra el fondo -- QA propia al tocar esta paleta).
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

  // Una serie por nivel de la rampa (0-4), apiladas -- colores de
  // COLOR_BANDA_POR_NIVEL (arriba), solo para esta gráfica.
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

  // QA (ronda 2, hallazgo #1): el título de esta tarjeta promete "tendencia
  // del índice", pero solo se dibujaba la distribución de trámites por nivel
  // (real, pero NO es el índice) -- con los 3 diagnósticos de la prueba, esa
  // distribución subía de 1 a 3 mientras el índice real se quedaba plano en
  // 0.0, dando la impresión visual (falsa) de que la madurez mejoraba. El
  // índice real ahora se dibuja encima, en su propio eje derecho (0-4, la
  // misma escala fija de siempre) y en tinta neutra -- un color que no es
  // ninguno de los 5 de la rampa, para que se lea como "la cifra", no como
  // "un nivel más". `z` alto para que la línea quede sobre las áreas
  // apiladas, nunca tapada por ellas.
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
    // Exportar como imagen (pedido explícito, mismo motivo que el tooltip real:
    // reemplazar el SVG hecho a mano de antes por algo que un funcionario pueda
    // guardar y compartir tal cual).
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
        // Sin rango fijo -- a diferencia del índice, esto cuenta TRÁMITES, y
        // ese total crece con el catálogo del gobierno.
        minInterval: 1,
        splitLine: { lineStyle: { color: colorBorde, type: "dashed", opacity: 0.4 } },
        axisLabel: { color: colorTexto, fontSize: 11 },
        axisLine: { show: false },
      },
      {
        type: "value",
        name: "Índice",
        nameTextStyle: { color: colorTexto, fontSize: 10 },
        // Rango fijo 0-4 -- es el rango real del índice, no el mínimo/máximo
        // de los datos: así un salto de 3 a 4 se ve igual de grande que uno
        // de 0 a 1 en cualquier momento que se mire el panel.
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
        const fecha = formatearFechaHora(puntos[lista[0].dataIndex ?? 0].creado_en);
        const filas = lista.map((p) => {
          const marcador = typeof p.marker === "string" ? p.marker : "";
          const numero = typeof p.value === "number" ? p.value : Number(p.value);
          const valor = p.seriesName === NOMBRE_SERIE_INDICE ? numero.toFixed(1) : String(numero);
          return `${marcador} ${p.seriesName}: <strong>${valor}</strong>`;
        });
        return [fecha, ...filas].join("<br/>");
      },
    },
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
  // Con 0-1 puntos no hay "tendencia" que mostrar -- un dibujo con un solo
  // punto sería más confuso que útil (docs/ux-brief.md, "sin producto de
  // consumo": no rellenar con algo que parezca dato sin serlo).
  const opcion = useMemo(() => (puntos.length >= 2 ? construirOpcion(puntos) : null), [puntos]);

  const contenedorRef = useRef<HTMLDivElement>(null);
  const graficaRef = useRef<echarts.ECharts | null>(null);

  // Bug real (no de caché): un efecto de montaje con deps `[]` solo corre UNA
  // vez, justo después del primer commit -- pero mientras `historialQuery`
  // está en "cargando" o hay <2 puntos, este componente todavía no devuelve el
  // JSX con el <div ref={contenedorRef}>, así que ese primer efecto encontraba
  // `contenedorRef.current === null` y se quedaba así para siempre: para
  // cuando los datos reales llegaban y por fin se pintaba el <div>, el efecto
  // de montaje ya no iba a volver a correr, y `echarts.init` nunca se llamaba.
  // Ahora la creación es perezosa, dentro del mismo efecto que reacciona a
  // `opcion` -- corre cada vez que hay datos nuevos, y solo inicializa si
  // todavía no existe una instancia (o si el contenedor cambió, ej. al pasar
  // de "cargando" a "con datos" el <div> es un nodo del DOM distinto).
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

  // Efecto de limpieza -- solo se encarga del listener de resize y de liberar
  // la instancia al desmontar el componente, no de crearla (eso ya lo hace el
  // efecto de arriba, de forma perezosa).
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
    return (
      <p className="text-sm text-atenuado">
        Todavía no hay suficientes diagnósticos enviados para mostrar una tendencia (se necesitan al menos 2).
      </p>
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

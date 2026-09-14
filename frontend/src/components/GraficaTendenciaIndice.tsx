import { useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts/core";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { LineChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import type { ComposeOption } from "echarts/core";
import type { GridComponentOption, LegendComponentOption, TooltipComponentOption } from "echarts/components";
import type { LineSeriesOption } from "echarts/charts";

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
echarts.use([GridComponent, LegendComponent, TooltipComponent, LineChart, CanvasRenderer]);

type OpcionGrafica = ComposeOption<GridComponentOption | LegendComponentOption | TooltipComponentOption | LineSeriesOption>;

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

function formatearFechaCorta(fechaIso: string): string {
  return new Date(fechaIso).toLocaleDateString("es", { day: "numeric", month: "short" });
}

function formatearFechaHora(fechaIso: string): string {
  return new Date(fechaIso).toLocaleString("es", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

// ECharts dibuja en <canvas>, que no entiende `var(--token)` -- solo colores
// resueltos. `nivel.varTexto` (frontend/src/lib/madurez.ts) y el resto de la
// paleta (frontend/src/index.css) siguen siendo la fuente de verdad; esto solo
// las resuelve a su hex/rgb real en el momento de dibujar, para que la
// gráfica respete el tema (claro/oscuro) sin duplicar ningún valor a mano.
function resolverColor(valorCss: string): string {
  const variable = valorCss.match(/^var\((--[\w-]+)\)$/)?.[1];
  if (!variable) return valorCss;
  return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
}

function construirOpcion(puntos: PuntoIndiceGlobalResponse[]): OpcionGrafica {
  const colorBorde = resolverColor("var(--border)");
  const colorTexto = resolverColor("var(--atenuado)");
  const colorTarjeta = resolverColor("var(--card)");
  const colorTextoTarjeta = resolverColor("var(--card-foreground)");

  // Una serie por nivel de la rampa (0-4), apiladas -- mismos 5 colores ya
  // validados de frontend/src/lib/madurez.ts, sin paleta nueva. `hexClaro` es
  // justo el uso para el que está pensado ese hex (decorativo, piso 2:1 --
  // ver el comentario de esa constante): nunca se usa aquí como texto ni
  // borde, solo como relleno de área.
  const series: LineSeriesOption[] = NIVELES_MADUREZ.map((nivel, i) => ({
    name: `${nivel.nivel} — ${nivel.etiqueta}`,
    type: "line",
    stack: "total",
    smooth: true,
    showSymbol: false,
    lineStyle: { width: 0 },
    areaStyle: { opacity: 0.85, color: nivel.hexClaro },
    emphasis: { focus: "series" },
    data: puntos.map((p) => p[CLAVE_CONTEO_POR_NIVEL[i]]),
  }));

  return {
    color: NIVELES_MADUREZ.map((n) => n.hexClaro),
    legend: {
      bottom: 0,
      itemWidth: 12,
      itemHeight: 12,
      textStyle: { color: colorTexto, fontSize: 11 },
    },
    grid: { left: 36, right: 12, top: 16, bottom: 56 },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: puntos.map((p) => formatearFechaCorta(p.creado_en)),
      axisLine: { lineStyle: { color: colorBorde } },
      axisLabel: { color: colorTexto, fontSize: 11 },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      // Sin rango fijo -- a diferencia del índice (siempre 0-4), esto cuenta
      // TRÁMITES, y ese total crece con el catálogo del gobierno.
      minInterval: 1,
      splitLine: { lineStyle: { color: colorBorde, type: "dashed", opacity: 0.4 } },
      axisLabel: { color: colorTexto, fontSize: 11 },
      axisLine: { show: false },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: colorTarjeta,
      borderColor: colorBorde,
      textStyle: { color: colorTextoTarjeta },
    },
    series,
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

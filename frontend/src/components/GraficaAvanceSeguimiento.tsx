import { useEffect, useMemo, useRef } from "react";

import * as echarts from "echarts/core";
import { LegendComponent, TooltipComponent } from "echarts/components";
import { PieChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import type { ComposeOption } from "echarts/core";
import type { LegendComponentOption, TooltipComponentOption } from "echarts/components";
import type { PieSeriesOption } from "echarts/charts";

import { resolverColorCss } from "@/lib/colorCss";
import { ESTADOS_SEMAFORO, ORDEN_ESTADOS_SEMAFORO, type EstadoSemaforo } from "@/lib/semaforo";
import type { AccionSeguimientoResponse } from "@/lib/seguimientoApi";

// % de avance del seguimiento -- pedido explícito del usuario: reproducir el
// look del ejemplo oficial de ECharts "Customized Pie" (roseType: 'radius',
// glow), con fondo blanco fijo (pedido explícito, no el fondo oscuro del
// ejemplo original) sin importar el modo claro/oscuro del resto del
// producto -- es una tarjeta con identidad visual propia, no una gráfica que
// deba theme-earse con resolverColorCss como el resto del kit.
//
// Nota de precisión de datos, ya comunicada y aceptada: un rose chart codifica
// el valor en el RADIO, así que el área crece al cuadrado del valor y
// distorsiona la magnitud real -- la alternativa correcta (barra apilada) es
// la que se usó en la primera versión de esta gráfica. El usuario pidió
// explícitamente ver esta versión de todas formas y juzgar él mismo si el
// resultado visual vale la pena frente a esa distorsión.
echarts.use([LegendComponent, TooltipComponent, PieChart, CanvasRenderer]);

type OpcionGrafica = ComposeOption<LegendComponentOption | TooltipComponentOption | PieSeriesOption>;

const FONDO_TARJETA = "#ffffff";
// Texto/líneas oscuras sobre el fondo blanco fijo de arriba -- mismo criterio
// que el ejemplo original (texto claro sobre fondo oscuro), solo invertido.
const TEXTO_SOBRE_FONDO = "rgba(30, 30, 28, 0.85)";
const TEXTO_ATENUADO_SOBRE_FONDO = "rgba(30, 30, 28, 0.65)";
const LINEA_SOBRE_FONDO = "rgba(30, 30, 28, 0.35)";

function construirOpcion(conteos: Record<EstadoSemaforo, number>, total: number): OpcionGrafica {
  // Orden ascendente por valor, igual que el ejemplo de referencia -- en un
  // rose chart el orden importa para la lectura visual (radios crecientes en
  // sentido horario desde el más chico).
  const datos = [...ORDEN_ESTADOS_SEMAFORO]
    .map((estado) => {
      const info = ESTADOS_SEMAFORO[estado];
      // `info.hex` es un string "var(--...)" (semaforo.ts), no un color ya
      // resuelto -- un <canvas> no entiende esa sintaxis, así que ECharts
      // caía al negro por default del navegador (bug reportado: círculo
      // negro sólido cuando una sola categoría llega al 100%). Mismo
      // resolvedor que ya usa GraficaTendenciaIndice.tsx para este problema.
      const color = resolverColorCss(info.hex);
      return {
        estado,
        name: `${info.icono} ${info.etiqueta}`,
        value: conteos[estado],
        itemStyle: {
          color,
          shadowBlur: 40,
          shadowColor: color,
        },
      };
    })
    .sort((a, b) => a.value - b.value);

  const serie: PieSeriesOption = {
    name: "Acciones de seguimiento",
    type: "pie",
    radius: "65%",
    center: ["50%", "50%"],
    roseType: "radius",
    data: datos,
    label: {
      color: TEXTO_SOBRE_FONDO,
      fontSize: 12,
      formatter: (parametros) => {
        const valor = Number(parametros.value);
        const pct = total > 0 ? Math.round((valor / total) * 100) : 0;
        return `${String(parametros.name)}\n${valor} (${pct}%)`;
      },
    },
    labelLine: {
      lineStyle: { color: LINEA_SOBRE_FONDO },
      smooth: 0.2,
      length: 8,
      length2: 12,
    },
    emphasis: { focus: "self" },
    animationType: "scale",
    animationEasing: "elasticOut",
    animationDelay: () => Math.random() * 200,
  };

  return {
    backgroundColor: FONDO_TARJETA,
    tooltip: {
      trigger: "item",
      backgroundColor: "#ffffff",
      borderColor: "rgba(30, 30, 28, 0.15)",
      textStyle: { color: "#1a1a19" },
      formatter: (parametros) => {
        const p = Array.isArray(parametros) ? parametros[0] : parametros;
        const valor = Number(p.value);
        const pct = total > 0 ? Math.round((valor / total) * 100) : 0;
        return `<strong>${valor}</strong> (${pct}%) · ${String(p.name)}`;
      },
    },
    legend: {
      bottom: 4,
      itemWidth: 12,
      itemHeight: 12,
      textStyle: { color: TEXTO_ATENUADO_SOBRE_FONDO, fontSize: 11 },
    },
    series: [serie],
  };
}

export function GraficaAvanceSeguimiento({ acciones }: { acciones: AccionSeguimientoResponse[] }) {
  const conteos = useMemo(() => {
    const base = { completado: 0, en_progreso: 0, atrasado: 0 } as Record<EstadoSemaforo, number>;
    for (const accion of acciones) {
      base[accion.estado_semaforo] += 1;
    }
    return base;
  }, [acciones]);

  const total = acciones.length;
  const opcion = useMemo(() => (total > 0 ? construirOpcion(conteos, total) : null), [conteos, total]);

  const contenedorRef = useRef<HTMLDivElement>(null);
  const graficaRef = useRef<echarts.ECharts | null>(null);

  // Mismo patrón de inicialización perezosa que GraficaTendenciaIndice.tsx --
  // ver el comentario extenso ahí sobre por qué no puede ser un efecto de
  // montaje con deps [].
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

  useEffect(() => {
    const alRedimensionar = () => graficaRef.current?.resize();
    window.addEventListener("resize", alRedimensionar);
    return () => {
      window.removeEventListener("resize", alRedimensionar);
      graficaRef.current?.dispose();
      graficaRef.current = null;
    };
  }, []);

  if (total === 0) return null;

  return (
    <div className="flex flex-col gap-1">
      <div ref={contenedorRef} style={{ width: "100%", height: 320, borderRadius: 12, overflow: "hidden" }} />
      {/* Fallback textual accesible -- mismas cifras que la gráfica, siempre
          visible, nunca depende de hover ni de leer el tamaño relativo de un
          radio (que además, por diseño de un rose chart, no es proporcional
          al valor -- ver nota de precisión de datos arriba). La tabla
          completa de acciones, con el detalle de cada una, ya vive justo
          debajo en esta misma pantalla. */}
      <p className="text-xs text-atenuado">
        {ORDEN_ESTADOS_SEMAFORO.map((estado, i) => (
          <span key={estado}>
            {i > 0 && " · "}
            {ESTADOS_SEMAFORO[estado].icono} {ESTADOS_SEMAFORO[estado].etiqueta}: {conteos[estado]}
          </span>
        ))}
        {" "}(de {total} {total === 1 ? "acción" : "acciones"})
      </p>
    </div>
  );
}

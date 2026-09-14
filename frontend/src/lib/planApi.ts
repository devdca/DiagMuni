import { ApiError, apiFetch } from "./httpClient";
import { obtenerToken } from "./session";

// Usado solo para el polling de "generando plan" (docs/app-flow.md línea 55) --
// GET /api/tramites/{id}/plan (backend/app/api/planes.py::obtener_plan_vigente)
// devuelve 404 mientras el plan no existe todavía, eso es esperado y no un error.
export async function planListo(tramiteId: string): Promise<boolean> {
  try {
    await apiFetch(`/api/tramites/${tramiteId}/plan`);
    return true;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return false;
    throw error;
  }
}

// Forma exacta confirmada leyendo backend/app/engine/catalogo_loader.py::componente_recomendado_para
// (líneas 92-128) -- cada campo de costo es un string (puede ser literalmente
// "[NO VERIFICADO]", ver backend/app/engine/catalogo/costos_oss.yaml), nunca un
// número: no se formatea como moneda acá, la pantalla decide cómo mostrarlo.
export interface CostoComponente {
  moneda_local: string;
  usd: string;
}

export interface ComponenteRecomendado {
  nombre_componente: string;
  licencia: string;
  url_repositorio: string;
  moneda_local_codigo: string;
  costo_licenciamiento: CostoComponente;
  costo_infraestructura: CostoComponente;
  costo_implementacion: CostoComponente;
  nota_advertencia: string | null;
  fuente_licencia: string;
  fuente_actividad: string;
  fuente_costo: string;
  fecha_verificacion: string;
}

// `componente_recomendado` siempre está presente en cada brecha, en ambos modos
// (`degradado` y `llm` llaman igual a componente_recomendado_para(), ver
// backend/app/engine/plantillas.py y backend/app/ia/generador_plan.py) -- `null`
// solo cuando `categoria_catalogo` no tiene componente OSS en el catálogo (la
// mayoría de las brechas normativas/organizacionales agregadas en Fase 1).
export interface Brecha {
  variable: string;
  narrativa: string;
  paso_administrativo: string;
  paso_tecnico: string;
  paso_organizacional: string;
  prerrequisitos: string[];
  por_que_importa: string;
  fuente_normativa: string;
  categoria_catalogo: string;
  componente_recomendado: ComponenteRecomendado | null;
}

// backend/app/engine/resumen_plan.py::calcular_resumen_inversion -- agregación
// determinista de `componente_recomendado` de todas las brechas, deduplicada por
// componente. `null` en un monto significa "sin dato verificado", no cero.
export interface MontoDual {
  moneda_local: string | null;
  usd: string | null;
}

export interface ResumenInversion {
  moneda_local_codigo: string;
  inversion_unica_estimada: MontoDual;
  costo_recurrente_mensual_estimado: MontoDual;
  componentes: ComponenteRecomendado[];
  brechas_totales: number;
  brechas_con_componente_software: number;
  nota_cobertura: string;
}

// backend/app/engine/catalogo/costos_personal.yaml -- salario_mensual_promedio
// puede ser literalmente "[NO VERIFICADO]" (caso Uruguay hoy).
export interface CostoReferenciaPersonal {
  puesto_referencia: string | null;
  salario_mensual_promedio: string;
  moneda: string;
  fuente: string;
  fecha_consulta: string;
}

// backend/app/engine/resumen_plan.py::calcular_resumen_personal
export interface ResumenPersonal {
  acciones_organizacionales: string[];
  personal_ti_actual: number | null;
  personal_total_gobierno: number | null;
  capacitacion_anual_vigente: boolean | null;
  costo_referencia_personal_ti: CostoReferenciaPersonal | null;
}

// backend/app/engine/resumen_plan.py::calcular_orden_sugerido -- agrupación por
// si la brecha tiene prerrequisitos pendientes o no, no un grafo de dependencias
// real (prerrequisitos es texto libre, ver el módulo backend).
export interface OrdenSugerido {
  sin_prerrequisitos: string[];
  con_prerrequisitos: string[];
}

// backend/app/engine/resumen_plan.py::calcular_progreso_historico -- diff contra
// la versión anterior del mismo diagnóstico, calculado en lectura (no vive en
// `contenido`). `null` en `PlanOut.progreso_historico` cuando es la primera versión.
export interface ProgresoHistorico {
  brechas_resueltas: string[];
  brechas_nuevas: string[];
  brechas_persistentes: string[];
}

// Complementaria a `brechas` (backend/app/ia/sugerencia_libre.py) -- generada a
// partir de la descripción libre del trámite + el perfil del gobierno, NUNCA pasa
// por el verificador F9 (a diferencia de `brechas`). `null` si el trámite no tiene
// descripción o no hay ninguna ruta de LLM disponible -- sin fallback determinista.
export interface SugerenciaLibre {
  texto: string;
  advertencia: string;
}

// backend/app/ia/estimacion_recursos.py -- misma naturaleza que SugerenciaLibre
// (texto libre de IA, no verificado), pero sobre personal/presupuesto en vez del
// enfoque del trámite. `null` sin brechas o sin ruta de LLM disponible.
export interface EstimacionRecursos {
  texto: string;
  advertencia: string;
}

export interface ContenidoPlan {
  resumen_narrativo: string;
  brechas: Brecha[];
  sugerencia_libre: SugerenciaLibre | null;
  resumen_inversion: ResumenInversion;
  resumen_personal: ResumenPersonal;
  orden_sugerido: OrdenSugerido;
  estimacion_recursos: EstimacionRecursos | null;
}

export interface PlanOut {
  id: string;
  diagnostico_tramite_id: string;
  version: number;
  modo: "llm" | "degradado";
  contenido: ContenidoPlan;
  verificado: boolean;
  generado_en: string;
  indice_madurez: number | null;
  progreso_historico: ProgresoHistorico | null;
}

export async function obtenerPlan(tramiteId: string): Promise<PlanOut> {
  return apiFetch<PlanOut>(`/api/tramites/${tramiteId}/plan`);
}

// Comparador de versiones (backend/app/adaptadores/http/planes.py::listar_versiones_plan
// / obtener_version_plan) -- a diferencia de PlanOut (siempre la vigente), estas
// dos rutas dejan traer cualquier versión histórica, nunca se borran.
export interface VersionPlanResumen {
  version: number;
  modo: "llm" | "degradado";
  verificado: boolean;
  generado_en: string;
  brechas_totales: number;
}

// Sin `indice_madurez`: `diagnostico_tramite` solo guarda el índice ACTUAL, no
// uno por versión de plan (ver backend/app/schemas/plan.py::PlanVersionDetalleOut).
export interface PlanVersionDetalle {
  version: number;
  modo: "llm" | "degradado";
  verificado: boolean;
  generado_en: string;
  contenido: ContenidoPlan;
}

export function obtenerVersionesPlan(tramiteId: string): Promise<VersionPlanResumen[]> {
  return apiFetch<VersionPlanResumen[]>(`/api/tramites/${tramiteId}/plan/versiones`);
}

export function obtenerVersionPlan(tramiteId: string, version: number): Promise<PlanVersionDetalle> {
  return apiFetch<PlanVersionDetalle>(`/api/tramites/${tramiteId}/plan/versiones/${version}`);
}

// No puede usar apiFetch (asume JSON) -- descarga el PDF como blob y dispara la
// descarga con un <a> temporal, que sí lleva el Authorization: Bearer (a
// diferencia de un <a href> plano apuntando directo al backend).
export async function descargarPlanPdf(tramiteId: string): Promise<void> {
  const token = obtenerToken();
  const respuesta = await fetch(`/api/tramites/${tramiteId}/plan/pdf`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!respuesta.ok) {
    throw new ApiError("No se pudo generar el PDF. Intenta de nuevo.", respuesta.status);
  }

  const blob = await respuesta.blob();
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = "plan-modernizacion.pdf";
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  URL.revokeObjectURL(url);
}

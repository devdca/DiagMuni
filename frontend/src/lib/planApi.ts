import { ApiError, apiFetch } from "./httpClient";
import { obtenerToken } from "./session";

// Polling de "generando plan" -- 404 mientras no existe todavía, no es un error.
export async function planListo(tramiteId: string): Promise<boolean> {
  try {
    await apiFetch(`/api/tramites/${tramiteId}/plan`);
    return true;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return false;
    throw error;
  }
}

// Cada costo es un string (puede ser literalmente "[NO VERIFICADO]"), nunca un
// número -- no se formatea como moneda acá, la pantalla decide cómo mostrarlo.
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

// `componente_recomendado` es `null` solo cuando esa categoría no tiene
// componente OSS en el catálogo (brechas normativas/organizacionales, sobre todo).
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

// `null` en un monto significa "sin dato verificado", no cero.
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

// `salario_mensual_promedio` puede ser literalmente "[NO VERIFICADO]".
export interface CostoReferenciaPersonal {
  puesto_referencia: string | null;
  salario_mensual_promedio: string;
  moneda: string;
  fuente: string;
  fecha_consulta: string;
}

export interface ResumenPersonal {
  acciones_organizacionales: string[];
  personal_ti_actual: number | null;
  personal_total_gobierno: number | null;
  capacitacion_anual_vigente: boolean | null;
  costo_referencia_personal_ti: CostoReferenciaPersonal | null;
}

// Agrupación por si la brecha tiene prerrequisitos pendientes, no un grafo real.
export interface OrdenSugerido {
  sin_prerrequisitos: string[];
  con_prerrequisitos: string[];
}

// Diff contra la versión anterior, calculado en lectura -- `null` en la primera versión.
export interface ProgresoHistorico {
  brechas_resueltas: string[];
  brechas_nuevas: string[];
  brechas_persistentes: string[];
}

// Complementaria a `brechas` -- NUNCA pasa por el verificador (a diferencia de
// `brechas`). `null` sin descripción del trámite o sin ruta de LLM disponible.
export interface SugerenciaLibre {
  texto: string;
  advertencia: string;
}

// Misma naturaleza que SugerenciaLibre (texto de IA sin verificar), sobre
// personal/presupuesto. `null` sin brechas o sin ruta de LLM disponible.
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

// Comparador de versiones -- a diferencia de PlanOut (siempre la vigente), esto
// trae cualquier versión histórica; nunca se borran.
export interface VersionPlanResumen {
  version: number;
  modo: "llm" | "degradado";
  verificado: boolean;
  generado_en: string;
  brechas_totales: number;
}

// Sin `indice_madurez`: el diagnóstico solo guarda el índice actual, no uno por versión.
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

// No usa apiFetch (asume JSON) -- descarga el PDF como blob con Authorization,
// a diferencia de un <a href> plano que no llevaría el header.
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

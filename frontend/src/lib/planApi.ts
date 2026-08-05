import { ApiError, apiFetch } from "./httpClient";

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

// `componente_recomendado` solo se agrega hoy en modo `degradado`
// (backend/app/engine/plantillas.py) -- en modo `llm` nunca viene
// (backend/app/ia/generador_plan.py no lo incluye, asimetría conocida, ver
// entregables/fase-2/catalogo-oss-wiring.md). Por eso es opcional acá.
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
  componente_recomendado?: ComponenteRecomendado | null;
}

export interface ContenidoPlan {
  resumen_narrativo: string;
  brechas: Brecha[];
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
}

export async function obtenerPlan(tramiteId: string): Promise<PlanOut> {
  return apiFetch<PlanOut>(`/api/tramites/${tramiteId}/plan`);
}

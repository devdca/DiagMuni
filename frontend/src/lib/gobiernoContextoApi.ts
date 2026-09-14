import { apiFetch } from "./httpClient";

// Forma exacta de GET/PUT /api/gobierno/contexto (backend/app/schemas/
// gobierno_contexto.py) -- las 7 variables de contexto y capacidad institucional
// (entregables/fase-2/variables-contexto-institucional.md), capturadas una sola
// vez por gobierno (tenant), nunca por trámite.
export type Conectividad = "estable" | "intermitente" | "deficiente" | "sin_conexion";

export type InfraestructuraFirmaElectronica = "propia" | "proveedor_externo" | "gobierno_estatal";

// Migración 0009 -- 8 enums nuevos, un type por cada uno.
export type PortalTramitesTipo = "portal_unico" | "paginas_independientes" | "ninguno";
export type SiNoSoloAlgunos = "si" | "no" | "solo_algunos";
export type MecanismoIdentidadEstandar =
  | "llave_mx"
  | "id_uruguay"
  | "propio"
  | "ninguno"
  | "varia_por_tramite"
  | "otro";
export type SiNoParcialmente = "si" | "no" | "parcialmente";
export type IncidenteCiberseguridad = "si" | "no" | "sin_registro";
export type RotacionPersonalTi = "baja" | "media" | "alta" | "no_se_mide";
export type DependenciaOutsourcingTi = "si_totalmente" | "si_parcialmente" | "no";

export interface ContextoInstitucionalResponse {
  tenant_id: string;
  poblacion_total: number | null;
  personal_total_gobierno: number | null;
  presupuesto_tic_anual: string | null;
  area_tic_existe: boolean | null;
  conectividad: Conectividad | null;
  normativa_local_emitida: boolean | null;
  autoridad_gobernanza_digital: boolean | null;
  agenda_simplificacion_publicada: boolean | null;
  portal_datos_abiertos_existe: boolean | null;
  linea_atencion_ciudadana_centralizada: boolean | null;
  capacitacion_personal_tic_anual: boolean | null;
  protocolo_ciberseguridad_existe: boolean | null;
  presupuesto_total_anual: string | null;
  numero_tramites_totales: number | null;
  ingresos_propios_porcentaje: number | null;
  numero_oficinas_atencion: number | null;
  enlace_notificado_formalmente: boolean | null;
  convenio_colaboracion_estado: boolean | null;
  personal_area_ti: number | null;
  infraestructura_firma_electronica: InfraestructuraFirmaElectronica | null;
  porcentaje_tramites_en_linea: number | null;
  porcentaje_tramites_en_linea_no_se_mide: boolean;
  portal_tramites_tipo: PortalTramitesTipo | null;
  pagos_electronicos_generalizados: SiNoSoloAlgunos | null;
  mecanismo_identidad_estandar: MecanismoIdentidadEstandar | null;
  interoperabilidad_entre_areas: SiNoParcialmente | null;
  inventario_sistemas_existe: boolean | null;
  politica_gobierno_datos_existe: boolean | null;
  respaldos_periodicos_existen: boolean | null;
  incidente_ciberseguridad_24meses: IncidenteCiberseguridad | null;
  certificacion_seguridad_externa: boolean | null;
  rotacion_personal_ti: RotacionPersonalTi | null;
  dependencia_outsourcing_ti: DependenciaOutsourcingTi | null;
  mide_tiempos_resolucion: boolean | null;
  mide_satisfaccion_ciudadana: boolean | null;
  tablero_indicadores_existe: boolean | null;
  fondos_digitalizacion_recibidos: boolean | null;
  fondos_digitalizacion_detalle: string | null;
  porcentaje_poblacion_acceso_internet: number | null;
  porcentaje_poblacion_acceso_internet_no_se_tiene_dato: boolean;
  accesibilidad_sistemas_discapacidad: SiNoParcialmente | null;
  catalogo_tramites_propio_existe: boolean | null;
  // Migración 0019 -- de dónde salió `poblacion_total`: "inegi_api" (botón
  // "Sincronizar con INEGI") o "manual" (lo escribió el funcionario). Nunca se
  // envía en el payload de PUT -- el backend la deriva solo.
  poblacion_total_fuente: "inegi_api" | "manual" | null;
  actualizado_en: string | null;
}

// Upsert parcial -- cada campo es opcional, un PUT puede tocar uno solo sin
// reenviar los demás (backend/app/api/gobierno_contexto.py::guardar_contexto).
// `presupuesto_tic_anual` viaja como `number` en el request (Pydantic acepta
// número o string para un campo `Decimal`) aunque la respuesta lo devuelva como
// `string` (representación exacta de un `Decimal`, sin redondeo de punto flotante).
export interface ContextoInstitucionalPayload {
  poblacion_total?: number;
  personal_total_gobierno?: number;
  presupuesto_tic_anual?: number;
  area_tic_existe?: boolean;
  conectividad?: Conectividad;
  normativa_local_emitida?: boolean;
  autoridad_gobernanza_digital?: boolean;
  agenda_simplificacion_publicada?: boolean;
  portal_datos_abiertos_existe?: boolean;
  linea_atencion_ciudadana_centralizada?: boolean;
  capacitacion_personal_tic_anual?: boolean;
  protocolo_ciberseguridad_existe?: boolean;
  presupuesto_total_anual?: number;
  numero_tramites_totales?: number;
  ingresos_propios_porcentaje?: number;
  numero_oficinas_atencion?: number;
  enlace_notificado_formalmente?: boolean;
  convenio_colaboracion_estado?: boolean;
  personal_area_ti?: number;
  infraestructura_firma_electronica?: InfraestructuraFirmaElectronica;
  porcentaje_tramites_en_linea?: number;
  porcentaje_tramites_en_linea_no_se_mide?: boolean;
  portal_tramites_tipo?: PortalTramitesTipo;
  pagos_electronicos_generalizados?: SiNoSoloAlgunos;
  mecanismo_identidad_estandar?: MecanismoIdentidadEstandar;
  interoperabilidad_entre_areas?: SiNoParcialmente;
  inventario_sistemas_existe?: boolean;
  politica_gobierno_datos_existe?: boolean;
  respaldos_periodicos_existen?: boolean;
  incidente_ciberseguridad_24meses?: IncidenteCiberseguridad;
  certificacion_seguridad_externa?: boolean;
  rotacion_personal_ti?: RotacionPersonalTi;
  dependencia_outsourcing_ti?: DependenciaOutsourcingTi;
  mide_tiempos_resolucion?: boolean;
  mide_satisfaccion_ciudadana?: boolean;
  tablero_indicadores_existe?: boolean;
  fondos_digitalizacion_recibidos?: boolean;
  fondos_digitalizacion_detalle?: string;
  porcentaje_poblacion_acceso_internet?: number;
  porcentaje_poblacion_acceso_internet_no_se_tiene_dato?: boolean;
  accesibilidad_sistemas_discapacidad?: SiNoParcialmente;
  catalogo_tramites_propio_existe?: boolean;
}

// Nunca 404 -- si el tenant todavía no guardó ningún campo, el backend sintetiza
// el shape completo con los 8 campos de negocio en null.
export function obtenerContextoInstitucional(): Promise<ContextoInstitucionalResponse> {
  return apiFetch<ContextoInstitucionalResponse>("/api/gobierno/contexto");
}

export function guardarContextoInstitucional(
  payload: ContextoInstitucionalPayload,
): Promise<ContextoInstitucionalResponse> {
  return apiFetch<ContextoInstitucionalResponse>("/api/gobierno/contexto", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

// Botón "Sincronizar con INEGI" del Perfil del gobierno -- trae poblacion_total
// real desde la API de Indicadores de INEGI (backend/app/adaptadores/inegi/).
// 422 si el gobierno no tiene clave_geoestadistica configurada, o si INEGI no
// está disponible/configurado en este ambiente -- ver `ApiError` en httpClient.
export function sincronizarPoblacionInegi(): Promise<ContextoInstitucionalResponse> {
  return apiFetch<ContextoInstitucionalResponse>("/api/gobierno/contexto/sincronizar-poblacion-inegi", {
    method: "POST",
  });
}

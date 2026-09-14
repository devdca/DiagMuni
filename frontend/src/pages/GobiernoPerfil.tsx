import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Textarea } from "@/components/ui/textarea";
import {
  type Conectividad,
  type ContextoInstitucionalPayload,
  type ContextoInstitucionalResponse,
  type DependenciaOutsourcingTi,
  type IncidenteCiberseguridad,
  type InfraestructuraFirmaElectronica,
  type MecanismoIdentidadEstandar,
  type PortalTramitesTipo,
  type RotacionPersonalTi,
  type SiNoParcialmente,
  type SiNoSoloAlgunos,
  guardarContextoInstitucional,
  obtenerContextoInstitucional,
  sincronizarPoblacionInegi,
} from "@/lib/gobiernoContextoApi";
import { ApiError } from "@/lib/httpClient";
import { obtenerPais } from "@/lib/session";
import { cn } from "@/lib/utils";

// Pantalla "Perfil del gobierno" (docs/ux-brief.md sección 6, docs/app-flow.md
// ruta /gobierno/perfil): las 7 variables de contexto y capacidad institucional
// del gobierno, capturadas una sola vez por tenant, nunca por trámite. Sin noción
// de "enviar cuestionario completo" -- cada campo se guarda de forma independiente
// (autosave) apenas el funcionario lo confirma, no hay estado "incompleto" que
// bloquee nada (entregables/fase-2/variables-contexto-institucional.md, sección
// 4.1). Los campos discretos (RadioGroup, Select) guardan al elegir una opción;
// los numéricos guardan al salir del campo (onBlur), para no disparar una llamada
// por cada tecla.

const CONECTIVIDAD_OPCIONES: { valor: Conectividad; etiqueta: string }[] = [
  { valor: "estable", etiqueta: "Estable" },
  { valor: "intermitente", etiqueta: "Intermitente" },
  { valor: "deficiente", etiqueta: "Deficiente" },
  { valor: "sin_conexion", etiqueta: "Sin conexión" },
];

const INFRAESTRUCTURA_FIRMA_ELECTRONICA_OPCIONES: { valor: InfraestructuraFirmaElectronica; etiqueta: string }[] = [
  { valor: "propia", etiqueta: "Infraestructura propia" },
  { valor: "proveedor_externo", etiqueta: "Proveedor externo" },
  { valor: "gobierno_estatal", etiqueta: "La provee el gobierno estatal/nacional" },
];

const PORTAL_TRAMITES_OPCIONES: { valor: PortalTramitesTipo; etiqueta: string }[] = [
  { valor: "portal_unico", etiqueta: "Portal único de trámites" },
  { valor: "paginas_independientes", etiqueta: "Cada dependencia tiene su propia página" },
  { valor: "ninguno", etiqueta: "No existe ninguno" },
];

const SI_NO_SOLO_ALGUNOS_OPCIONES: { valor: SiNoSoloAlgunos; etiqueta: string }[] = [
  { valor: "si", etiqueta: "Sí" },
  { valor: "no", etiqueta: "No" },
  { valor: "solo_algunos", etiqueta: "Solo para algunos trámites" },
];

const MECANISMO_IDENTIDAD_ESTANDAR_OPCIONES: { valor: MecanismoIdentidadEstandar; etiqueta: string }[] = [
  { valor: "llave_mx", etiqueta: "Llave MX" },
  { valor: "id_uruguay", etiqueta: "ID Uruguay" },
  { valor: "propio", etiqueta: "Mecanismo propio del gobierno" },
  { valor: "ninguno", etiqueta: "Ninguno" },
  { valor: "varia_por_tramite", etiqueta: "Varía según el trámite" },
  { valor: "otro", etiqueta: "Otro" },
];

const SI_NO_PARCIALMENTE_OPCIONES: { valor: SiNoParcialmente; etiqueta: string }[] = [
  { valor: "si", etiqueta: "Sí" },
  { valor: "no", etiqueta: "No" },
  { valor: "parcialmente", etiqueta: "Parcialmente" },
];

const INCIDENTE_CIBERSEGURIDAD_OPCIONES: { valor: IncidenteCiberseguridad; etiqueta: string }[] = [
  { valor: "si", etiqueta: "Sí" },
  { valor: "no", etiqueta: "No" },
  { valor: "sin_registro", etiqueta: "No se tiene registro" },
];

const ROTACION_PERSONAL_TI_OPCIONES: { valor: RotacionPersonalTi; etiqueta: string }[] = [
  { valor: "baja", etiqueta: "Baja" },
  { valor: "media", etiqueta: "Media" },
  { valor: "alta", etiqueta: "Alta" },
  { valor: "no_se_mide", etiqueta: "No se mide" },
];

const DEPENDENCIA_OUTSOURCING_OPCIONES: { valor: DependenciaOutsourcingTi; etiqueta: string }[] = [
  { valor: "si_totalmente", etiqueta: "Sí, totalmente" },
  { valor: "si_parcialmente", etiqueta: "Sí, parcialmente" },
  { valor: "no", etiqueta: "No" },
];

function preguntaAutoridadGobernanza(pais: string | null): string {
  if (pais === "uy") {
    return "¿Existe un convenio vigente con Agesic para asesoría en transformación digital?";
  }
  if (pais === "mx") {
    return "¿Existe la Autoridad Municipal de Simplificación y Digitalización (con sus 5 áreas sustantivas) y su Enlace designado?";
  }
  // pais aún no resuelto (token viejo sin el claim -- ver session.ts, obtenerPais)
  // -- mismo criterio que Diagnostico.tsx (opcionesMecanismo), que no presume
  // ningún país mientras el claim no llegó: pregunta neutra en vez de citar la
  // norma de un país que puede no corresponderle a este gobierno.
  return "¿Existe la autoridad o el convenio de gobernanza digital que corresponde a tu gobierno (Autoridad Municipal de Simplificación y Digitalización en México; convenio con Agesic en Uruguay)?";
}

function EstadoGuardado({ guardando, error }: { guardando: boolean; error: boolean }) {
  if (error) return <p className="text-xs text-destructive">No se pudo guardar. Intenta de nuevo.</p>;
  if (guardando) return <p className="text-xs text-atenuado">Guardando…</p>;
  return null;
}

function CampoBooleano({
  pregunta,
  ayuda,
  valor,
  guardando,
  error,
  onCambiar,
}: {
  pregunta: string;
  ayuda?: string;
  valor: boolean | null;
  guardando: boolean;
  error: boolean;
  onCambiar: (valor: boolean) => void;
}) {
  const id = pregunta.slice(0, 20);
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-medium">{pregunta}</p>
      <RadioGroup
        value={valor === null ? undefined : valor ? "si" : "no"}
        onValueChange={(v) => onCambiar(v === "si")}
        className="grid grid-cols-2 gap-3 sm:w-64"
      >
        {(["si", "no"] as const).map((opcion) => (
          <label
            key={opcion}
            htmlFor={`${id}-${opcion}`}
            className={cn(
              "flex min-h-11 cursor-pointer items-center gap-3 rounded-md border px-3 py-2",
              (valor === true && opcion === "si") || (valor === false && opcion === "no")
                ? "border-primary"
                : "border-border",
            )}
          >
            <RadioGroupItem value={opcion} id={`${id}-${opcion}`} />
            <span className="text-sm">{opcion === "si" ? "Sí" : "No"}</span>
          </label>
        ))}
      </RadioGroup>
      {ayuda && <p className="text-xs text-atenuado">{ayuda}</p>}
      <EstadoGuardado guardando={guardando} error={error} />
    </div>
  );
}

// QA (ronda 2, hallazgo #5): un valor fuera de rango (ej. población -500, o
// -- para CampoPorcentajeConBandera de abajo -- un porcentaje de 150) se
// descartaba en el `onBlur` sin decir nada: ni error visible, ni el campo se
// revertía, ni el valor inválido se guardaba -- el funcionario veía su "150"
// seguir ahí como si se hubiera guardado, y solo se enteraba de que nunca se
// guardó si recargaba la página semanas después. `min`/`max` ahora son props
// reales (antes `min={0}` estaba fijo a mano y el tope superior, cuando
// existía, vivía suelto en el `onGuardar` del llamador -- ver
// ingresos_propios_porcentaje más abajo, que además nunca tuvo el atributo
// HTML `max`). El mensaje de error se muestra junto al campo y se limpia en
// cuanto el funcionario vuelve a escribir -- nunca se guarda ni se descarta
// en silencio.
function CampoNumerico({
  etiqueta,
  ayuda,
  valorInicial,
  guardando,
  error,
  min = 0,
  max,
  onGuardar,
}: {
  etiqueta: string;
  ayuda?: string;
  valorInicial: string;
  guardando: boolean;
  error: boolean;
  min?: number;
  max?: number;
  onGuardar: (valor: number) => void;
}) {
  const [valor, setValor] = useState(valorInicial);
  const [errorValidacion, setErrorValidacion] = useState<string | null>(null);

  useEffect(() => {
    setValor(valorInicial);
    setErrorValidacion(null);
  }, [valorInicial]);

  function validar(numero: number): string | null {
    if (!Number.isFinite(numero)) return "Escribe un número válido.";
    if (numero < min) return `El valor mínimo es ${min}.`;
    if (max !== undefined && numero > max) return `El valor máximo es ${max}.`;
    return null;
  }

  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium">{etiqueta}</label>
      <Input
        type="number"
        min={min}
        max={max}
        inputMode="numeric"
        value={valor}
        aria-invalid={errorValidacion !== null}
        onChange={(e) => {
          setValor(e.target.value);
          if (errorValidacion) setErrorValidacion(null);
        }}
        onBlur={() => {
          if (valor.trim() === "" || valor === valorInicial) return;
          const numero = Number(valor);
          const mensaje = validar(numero);
          if (mensaje) {
            setErrorValidacion(mensaje);
            return;
          }
          onGuardar(numero);
        }}
        className="sm:w-64"
      />
      {ayuda && <p className="text-xs text-atenuado">{ayuda}</p>}
      {errorValidacion && <p className="text-xs text-destructive">{errorValidacion}</p>}
      <EstadoGuardado guardando={guardando} error={error} />
    </div>
  );
}

function CampoConectividad({
  valor,
  guardando,
  error,
  onCambiar,
}: {
  valor: Conectividad | null;
  guardando: boolean;
  error: boolean;
  onCambiar: (valor: Conectividad) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor="conectividad" className="text-sm font-medium">
        ¿Cómo describiría la conectividad a internet de las oficinas donde se atienden trámites?
      </label>
      <select
        id="conectividad"
        value={valor ?? ""}
        onChange={(e) => onCambiar(e.target.value as Conectividad)}
        className="min-h-11 w-full max-w-64 rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        <option value="" disabled>
          Seleccione una opción
        </option>
        {CONECTIVIDAD_OPCIONES.map((opcion) => (
          <option key={opcion.valor} value={opcion.valor}>
            {opcion.etiqueta}
          </option>
        ))}
      </select>
      <EstadoGuardado guardando={guardando} error={error} />
    </div>
  );
}

// Genérico -- reemplaza los ~8 selects casi idénticos que este perfil necesita
// (infraestructura FEA + los 7 enums nuevos de migración 0009). Mismo patrón
// visual que CampoConectividad, sin duplicar el markup por cada enum.
function CampoSelect<T extends string>({
  id,
  etiqueta,
  ayuda,
  opciones,
  valor,
  guardando,
  error,
  onCambiar,
}: {
  id: string;
  etiqueta: string;
  ayuda?: string;
  opciones: { valor: T; etiqueta: string }[];
  valor: T | null;
  guardando: boolean;
  error: boolean;
  onCambiar: (valor: T) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-medium">
        {etiqueta}
      </label>
      <select
        id={id}
        value={valor ?? ""}
        onChange={(e) => onCambiar(e.target.value as T)}
        className="min-h-11 w-full max-w-64 rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        <option value="" disabled>
          Seleccione una opción
        </option>
        {opciones.map((opcion) => (
          <option key={opcion.valor} value={opcion.valor}>
            {opcion.etiqueta}
          </option>
        ))}
      </select>
      {ayuda && <p className="text-xs text-atenuado">{ayuda}</p>}
      <EstadoGuardado guardando={guardando} error={error} />
    </div>
  );
}

// Campo compuesto: número 0-100 + casilla "no se mide"/"no se tiene el dato",
// respuesta explícita distinta de "todavía no se llenó" (ver migración 0009).
function CampoPorcentajeConBandera({
  etiqueta,
  textoBandera,
  ayuda,
  valorInicial,
  bandera,
  guardando,
  error,
  onGuardarValor,
  onCambiarBandera,
}: {
  etiqueta: string;
  textoBandera: string;
  ayuda?: string;
  valorInicial: string;
  bandera: boolean;
  guardando: boolean;
  error: boolean;
  onGuardarValor: (valor: number) => void;
  onCambiarBandera: (valor: boolean) => void;
}) {
  const [valor, setValor] = useState(valorInicial);
  const [errorValidacion, setErrorValidacion] = useState<string | null>(null);

  useEffect(() => {
    setValor(valorInicial);
    setErrorValidacion(null);
  }, [valorInicial]);

  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium">{etiqueta}</label>
      {!bandera && (
        <>
          <Input
            type="number"
            min={0}
            max={100}
            inputMode="numeric"
            value={valor}
            aria-invalid={errorValidacion !== null}
            onChange={(e) => {
              setValor(e.target.value);
              if (errorValidacion) setErrorValidacion(null);
            }}
            onBlur={() => {
              // Mismo criterio que CampoNumerico -- ver su comentario: nunca
              // descartar en silencio, siempre decir por qué no se guardó.
              if (valor.trim() === "" || valor === valorInicial) return;
              const numero = Number(valor);
              if (!Number.isFinite(numero)) {
                setErrorValidacion("Escribe un número válido.");
                return;
              }
              if (numero < 0 || numero > 100) {
                setErrorValidacion("Escribe un número de 0 a 100.");
                return;
              }
              onGuardarValor(numero);
            }}
            className="sm:w-64"
          />
          {errorValidacion && <p className="text-xs text-destructive">{errorValidacion}</p>}
        </>
      )}
      <label className="flex items-center gap-2 text-xs text-atenuado">
        <input type="checkbox" checked={bandera} onChange={(e) => onCambiarBandera(e.target.checked)} />
        {textoBandera}
      </label>
      {ayuda && <p className="text-xs text-atenuado">{ayuda}</p>}
      <EstadoGuardado guardando={guardando} error={error} />
    </div>
  );
}

export function GobiernoPerfil() {
  const pais = obtenerPais();
  const queryClient = useQueryClient();
  const inicializadoRef = useRef(false);

  const [poblacionTotal, setPoblacionTotal] = useState("");
  // Migración 0019 -- de dónde salió `poblacion_total`: badge "Fuente: INEGI"
  // solo cuando vino del botón de sincronización, nunca cuando el funcionario
  // lo escribió a mano (backend/app/aplicacion/sincronizacion_inegi.py).
  const [poblacionTotalFuente, setPoblacionTotalFuente] = useState<ContextoInstitucionalResponse["poblacion_total_fuente"]>(null);
  const [errorInegi, setErrorInegi] = useState<string | null>(null);
  const [personalTotalGobierno, setPersonalTotalGobierno] = useState("");
  const [presupuestoTicAnual, setPresupuestoTicAnual] = useState("");
  const [presupuestoTotalAnual, setPresupuestoTotalAnual] = useState("");
  const [numeroTramitesTotales, setNumeroTramitesTotales] = useState("");
  const [ingresosPropiosPorcentaje, setIngresosPropiosPorcentaje] = useState("");
  const [numeroOficinasAtencion, setNumeroOficinasAtencion] = useState("");
  const [areaTicExiste, setAreaTicExiste] = useState<boolean | null>(null);
  const [conectividad, setConectividad] = useState<Conectividad | null>(null);
  const [normativaLocalEmitida, setNormativaLocalEmitida] = useState<boolean | null>(null);
  const [autoridadGobernanzaDigital, setAutoridadGobernanzaDigital] = useState<boolean | null>(null);
  const [agendaSimplificacionPublicada, setAgendaSimplificacionPublicada] = useState<boolean | null>(null);
  const [portalDatosAbiertosExiste, setPortalDatosAbiertosExiste] = useState<boolean | null>(null);
  const [lineaAtencionCiudadanaCentralizada, setLineaAtencionCiudadanaCentralizada] = useState<boolean | null>(null);
  const [capacitacionPersonalTicAnual, setCapacitacionPersonalTicAnual] = useState<boolean | null>(null);
  const [protocoloCiberseguridadExiste, setProtocoloCiberseguridadExiste] = useState<boolean | null>(null);
  const [enlaceNotificadoFormalmente, setEnlaceNotificadoFormalmente] = useState<boolean | null>(null);
  const [convenioColaboracionEstado, setConvenioColaboracionEstado] = useState<boolean | null>(null);
  const [personalAreaTi, setPersonalAreaTi] = useState("");
  const [infraestructuraFirmaElectronica, setInfraestructuraFirmaElectronica] =
    useState<InfraestructuraFirmaElectronica | null>(null);

  // Migración 0009 -- madurez digital transversal, interoperabilidad,
  // ciberseguridad, capital humano de TI, medición, financiamiento, accesibilidad.
  const [porcentajeTramitesEnLinea, setPorcentajeTramitesEnLinea] = useState("");
  const [porcentajeTramitesEnLineaNoSeMide, setPorcentajeTramitesEnLineaNoSeMide] = useState(false);
  const [portalTramitesTipo, setPortalTramitesTipo] = useState<PortalTramitesTipo | null>(null);
  const [pagosElectronicosGeneralizados, setPagosElectronicosGeneralizados] = useState<SiNoSoloAlgunos | null>(null);
  const [mecanismoIdentidadEstandar, setMecanismoIdentidadEstandar] = useState<MecanismoIdentidadEstandar | null>(
    null,
  );
  const [interoperabilidadEntreAreas, setInteroperabilidadEntreAreas] = useState<SiNoParcialmente | null>(null);
  const [inventarioSistemasExiste, setInventarioSistemasExiste] = useState<boolean | null>(null);
  const [politicaGobiernoDatosExiste, setPoliticaGobiernoDatosExiste] = useState<boolean | null>(null);
  const [respaldosPeriodicosExisten, setRespaldosPeriodicosExisten] = useState<boolean | null>(null);
  const [incidenteCiberseguridad24meses, setIncidenteCiberseguridad24meses] =
    useState<IncidenteCiberseguridad | null>(null);
  const [certificacionSeguridadExterna, setCertificacionSeguridadExterna] = useState<boolean | null>(null);
  const [rotacionPersonalTi, setRotacionPersonalTi] = useState<RotacionPersonalTi | null>(null);
  const [dependenciaOutsourcingTi, setDependenciaOutsourcingTi] = useState<DependenciaOutsourcingTi | null>(null);
  const [mideTiemposResolucion, setMideTiemposResolucion] = useState<boolean | null>(null);
  const [mideSatisfaccionCiudadana, setMideSatisfaccionCiudadana] = useState<boolean | null>(null);
  const [tableroIndicadoresExiste, setTableroIndicadoresExiste] = useState<boolean | null>(null);
  const [fondosDigitalizacionRecibidos, setFondosDigitalizacionRecibidos] = useState<boolean | null>(null);
  const [fondosDigitalizacionDetalle, setFondosDigitalizacionDetalle] = useState("");
  const [porcentajePoblacionAccesoInternet, setPorcentajePoblacionAccesoInternet] = useState("");
  const [porcentajePoblacionAccesoInternetNoSeTieneDato, setPorcentajePoblacionAccesoInternetNoSeTieneDato] =
    useState(false);
  const [accesibilidadSistemasDiscapacidad, setAccesibilidadSistemasDiscapacidad] =
    useState<SiNoParcialmente | null>(null);
  const [catalogoTramitesPropioExiste, setCatalogoTramitesPropioExiste] = useState<boolean | null>(null);

  const [campoGuardando, setCampoGuardando] = useState<string | null>(null);
  const [campoConError, setCampoConError] = useState<string | null>(null);

  const contextoQuery = useQuery({
    queryKey: ["gobierno-contexto"],
    queryFn: obtenerContextoInstitucional,
  });

  // Aplica los datos del servidor a TODOS los campos locales -- usado tanto al
  // cargar la página como después de cada guardado exitoso (ver guardarMutacion
  // más abajo). Antes solo corría una vez al montar (guardia de inicializadoRef,
  // ver abajo); si esta pantalla llevaba rato abierta y el dato real se
  // actualizaba por otro lado mientras tanto (ej. por API directa), esta pestaña
  // se quedaba mostrando el valor viejo para siempre -- y un guardado posterior
  // de OTRO campo, al hacer setQueryData con la respuesta completa del servidor,
  // nunca sincronizaba los campos que ya se habían "inicializado". Resincronizar
  // tras cada guardado exitoso cierra ese hueco sin perder la protección contra
  // pisar una edición en curso (nada dispara esto mientras el usuario solo escribe).
  function aplicarDatos(datos: ContextoInstitucionalResponse) {
    if (datos.poblacion_total !== null) setPoblacionTotal(String(datos.poblacion_total));
    setPoblacionTotalFuente(datos.poblacion_total_fuente);
    if (datos.personal_total_gobierno !== null) setPersonalTotalGobierno(String(datos.personal_total_gobierno));
    if (datos.presupuesto_tic_anual !== null) setPresupuestoTicAnual(String(datos.presupuesto_tic_anual));
    if (datos.presupuesto_total_anual !== null) setPresupuestoTotalAnual(String(datos.presupuesto_total_anual));
    if (datos.numero_tramites_totales !== null) setNumeroTramitesTotales(String(datos.numero_tramites_totales));
    if (datos.ingresos_propios_porcentaje !== null) {
      setIngresosPropiosPorcentaje(String(datos.ingresos_propios_porcentaje));
    }
    if (datos.numero_oficinas_atencion !== null) setNumeroOficinasAtencion(String(datos.numero_oficinas_atencion));
    if (datos.personal_area_ti !== null) setPersonalAreaTi(String(datos.personal_area_ti));
    setAreaTicExiste(datos.area_tic_existe);
    setConectividad(datos.conectividad);
    setNormativaLocalEmitida(datos.normativa_local_emitida);
    setAutoridadGobernanzaDigital(datos.autoridad_gobernanza_digital);
    setAgendaSimplificacionPublicada(datos.agenda_simplificacion_publicada);
    setPortalDatosAbiertosExiste(datos.portal_datos_abiertos_existe);
    setLineaAtencionCiudadanaCentralizada(datos.linea_atencion_ciudadana_centralizada);
    setCapacitacionPersonalTicAnual(datos.capacitacion_personal_tic_anual);
    setProtocoloCiberseguridadExiste(datos.protocolo_ciberseguridad_existe);
    setEnlaceNotificadoFormalmente(datos.enlace_notificado_formalmente);
    setConvenioColaboracionEstado(datos.convenio_colaboracion_estado);
    setInfraestructuraFirmaElectronica(datos.infraestructura_firma_electronica);

    if (datos.porcentaje_tramites_en_linea !== null) {
      setPorcentajeTramitesEnLinea(String(datos.porcentaje_tramites_en_linea));
    }
    setPorcentajeTramitesEnLineaNoSeMide(datos.porcentaje_tramites_en_linea_no_se_mide);
    setPortalTramitesTipo(datos.portal_tramites_tipo);
    setPagosElectronicosGeneralizados(datos.pagos_electronicos_generalizados);
    setMecanismoIdentidadEstandar(datos.mecanismo_identidad_estandar);
    setInteroperabilidadEntreAreas(datos.interoperabilidad_entre_areas);
    setInventarioSistemasExiste(datos.inventario_sistemas_existe);
    setPoliticaGobiernoDatosExiste(datos.politica_gobierno_datos_existe);
    setRespaldosPeriodicosExisten(datos.respaldos_periodicos_existen);
    setIncidenteCiberseguridad24meses(datos.incidente_ciberseguridad_24meses);
    setCertificacionSeguridadExterna(datos.certificacion_seguridad_externa);
    setRotacionPersonalTi(datos.rotacion_personal_ti);
    setDependenciaOutsourcingTi(datos.dependencia_outsourcing_ti);
    setMideTiemposResolucion(datos.mide_tiempos_resolucion);
    setMideSatisfaccionCiudadana(datos.mide_satisfaccion_ciudadana);
    setTableroIndicadoresExiste(datos.tablero_indicadores_existe);
    setFondosDigitalizacionRecibidos(datos.fondos_digitalizacion_recibidos);
    if (datos.fondos_digitalizacion_detalle !== null) setFondosDigitalizacionDetalle(datos.fondos_digitalizacion_detalle);
    if (datos.porcentaje_poblacion_acceso_internet !== null) {
      setPorcentajePoblacionAccesoInternet(String(datos.porcentaje_poblacion_acceso_internet));
    }
    setPorcentajePoblacionAccesoInternetNoSeTieneDato(datos.porcentaje_poblacion_acceso_internet_no_se_tiene_dato);
    setAccesibilidadSistemasDiscapacidad(datos.accesibilidad_sistemas_discapacidad);
    setCatalogoTramitesPropioExiste(datos.catalogo_tramites_propio_existe);
  }

  useEffect(() => {
    const datos = contextoQuery.data;
    if (!datos || inicializadoRef.current) return;
    inicializadoRef.current = true;
    aplicarDatos(datos);
  }, [contextoQuery.data]);

  const guardarMutacion = useMutation({
    mutationFn: (payload: ContextoInstitucionalPayload) => guardarContextoInstitucional(payload),
    onSuccess: (respuesta: ContextoInstitucionalResponse) => {
      queryClient.setQueryData(["gobierno-contexto"], respuesta);
      aplicarDatos(respuesta);
    },
  });

  function guardarCampo(campo: string, payload: ContextoInstitucionalPayload) {
    setCampoGuardando(campo);
    setCampoConError(null);
    guardarMutacion.mutate(payload, {
      onSettled: () => setCampoGuardando((actual) => (actual === campo ? null : actual)),
      onError: () => setCampoConError(campo),
    });
  }

  // Botón "Sincronizar con INEGI" -- trae `poblacion_total` real desde la API de
  // Indicadores de INEGI (backend/app/adaptadores/inegi/), en vez de que el
  // funcionario lo escriba a mano. El backend responde 422 con un `detail` en
  // lenguaje llano si el gobierno no tiene `clave_geoestadistica` configurada o
  // si INEGI no está disponible -- ese texto ya viene listo para mostrar tal
  // cual (mismo criterio que `ApiError.message` en el resto de la app).
  const sincronizarInegiMutacion = useMutation({
    mutationFn: sincronizarPoblacionInegi,
    onSuccess: (respuesta: ContextoInstitucionalResponse) => {
      setErrorInegi(null);
      queryClient.setQueryData(["gobierno-contexto"], respuesta);
      aplicarDatos(respuesta);
    },
    onError: (error: unknown) => {
      setErrorInegi(error instanceof ApiError ? error.message : "No se pudo sincronizar con INEGI.");
    },
  });

  if (contextoQuery.isLoading) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-sm text-atenuado">Cargando...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
      <div>
        <h2 className="text-lg font-semibold">Perfil del gobierno</h2>
        <p className="text-sm text-muted-foreground">
          Estos datos describen a todo el gobierno, no a un trámite en particular. Se capturan una sola vez y se
          pueden corregir cuando quieras.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Contexto</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <CampoNumerico
            etiqueta="¿Cuál es la población total del gobierno local (último dato oficial disponible)?"
            valorInicial={poblacionTotal}
            guardando={campoGuardando === "poblacion_total"}
            error={campoConError === "poblacion_total"}
            onGuardar={(valor) => {
              setPoblacionTotal(String(valor));
              guardarCampo("poblacion_total", { poblacion_total: valor });
            }}
          />
          <div className="-mt-2 flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={sincronizarInegiMutacion.isPending}
              onClick={() => sincronizarInegiMutacion.mutate()}
            >
              {sincronizarInegiMutacion.isPending ? "Sincronizando..." : "Sincronizar con INEGI"}
            </Button>
            {poblacionTotalFuente === "inegi_api" && (
              <span className="rounded-full border border-border bg-secondary px-2 py-0.5 text-xs text-atenuado">
                Fuente: INEGI
              </span>
            )}
          </div>
          {errorInegi && <p className="-mt-2 text-xs text-destructive">{errorInegi}</p>}
          <CampoNumerico
            etiqueta="¿Cuál es el total de personal del gobierno local (todas las áreas, no solo el trámite)?"
            valorInicial={personalTotalGobierno}
            guardando={campoGuardando === "personal_total_gobierno"}
            error={campoConError === "personal_total_gobierno"}
            onGuardar={(valor) => {
              setPersonalTotalGobierno(String(valor));
              guardarCampo("personal_total_gobierno", { personal_total_gobierno: valor });
            }}
          />
          <CampoNumerico
            etiqueta="¿Cuál es el presupuesto anual destinado a tecnologías de la información del gobierno local?"
            ayuda={pais === "uy" ? "Monto en UYU" : "Monto en MXN"}
            valorInicial={presupuestoTicAnual}
            guardando={campoGuardando === "presupuesto_tic_anual"}
            error={campoConError === "presupuesto_tic_anual"}
            onGuardar={(valor) => {
              setPresupuestoTicAnual(String(valor));
              guardarCampo("presupuesto_tic_anual", { presupuesto_tic_anual: valor });
            }}
          />
          <CampoNumerico
            etiqueta="¿Cuál es el presupuesto TOTAL anual del gobierno local (no solo TIC)?"
            ayuda={pais === "uy" ? "Monto en UYU -- da contexto de qué tan grande es el presupuesto de TIC en comparación" : "Monto en MXN -- da contexto de qué tan grande es el presupuesto de TIC en comparación"}
            valorInicial={presupuestoTotalAnual}
            guardando={campoGuardando === "presupuesto_total_anual"}
            error={campoConError === "presupuesto_total_anual"}
            onGuardar={(valor) => {
              setPresupuestoTotalAnual(String(valor));
              guardarCampo("presupuesto_total_anual", { presupuesto_total_anual: valor });
            }}
          />
          <CampoNumerico
            etiqueta="¿Cuántos trámites en total ofrece el gobierno local (no solo los ya diagnosticados aquí)?"
            valorInicial={numeroTramitesTotales}
            guardando={campoGuardando === "numero_tramites_totales"}
            error={campoConError === "numero_tramites_totales"}
            onGuardar={(valor) => {
              setNumeroTramitesTotales(String(valor));
              guardarCampo("numero_tramites_totales", { numero_tramites_totales: valor });
            }}
          />
          <CampoNumerico
            etiqueta="¿Qué porcentaje de los ingresos del gobierno son propios (no participaciones ni transferencias)?"
            ayuda="Un número de 0 a 100."
            valorInicial={ingresosPropiosPorcentaje}
            guardando={campoGuardando === "ingresos_propios_porcentaje"}
            error={campoConError === "ingresos_propios_porcentaje"}
            max={100}
            onGuardar={(valor) => {
              setIngresosPropiosPorcentaje(String(valor));
              guardarCampo("ingresos_propios_porcentaje", { ingresos_propios_porcentaje: valor });
            }}
          />
          <CampoNumerico
            etiqueta="¿Cuántas oficinas o ventanillas físicas de atención al público tiene el gobierno local?"
            valorInicial={numeroOficinasAtencion}
            guardando={campoGuardando === "numero_oficinas_atencion"}
            error={campoConError === "numero_oficinas_atencion"}
            onGuardar={(valor) => {
              setNumeroOficinasAtencion(String(valor));
              guardarCampo("numero_oficinas_atencion", { numero_oficinas_atencion: valor });
            }}
          />
          <CampoNumerico
            etiqueta="¿Cuántas personas conforman el área de TI del gobierno local?"
            ayuda="Distinto del personal total del gobierno de arriba -- solo el área de TI."
            valorInicial={personalAreaTi}
            guardando={campoGuardando === "personal_area_ti"}
            error={campoConError === "personal_area_ti"}
            onGuardar={(valor) => {
              setPersonalAreaTi(String(valor));
              guardarCampo("personal_area_ti", { personal_area_ti: valor });
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Capacidad institucional</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <CampoBooleano
            pregunta="¿El gobierno local cuenta con un área o responsable formalmente designado de tecnologías de la información?"
            valor={areaTicExiste}
            guardando={campoGuardando === "area_tic_existe"}
            error={campoConError === "area_tic_existe"}
            onCambiar={(valor) => {
              setAreaTicExiste(valor);
              guardarCampo("area_tic_existe", { area_tic_existe: valor });
            }}
          />
          <CampoConectividad
            valor={conectividad}
            guardando={campoGuardando === "conectividad"}
            error={campoConError === "conectividad"}
            onCambiar={(valor) => {
              setConectividad(valor);
              guardarCampo("conectividad", { conectividad: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿El gobierno local ha emitido normativa propia de simplificación o digitalización (reglamento, decreto o resolución municipal/departamental)?"
            valor={normativaLocalEmitida}
            guardando={campoGuardando === "normativa_local_emitida"}
            error={campoConError === "normativa_local_emitida"}
            onCambiar={(valor) => {
              setNormativaLocalEmitida(valor);
              guardarCampo("normativa_local_emitida", { normativa_local_emitida: valor });
            }}
          />
          <CampoBooleano
            pregunta={preguntaAutoridadGobernanza(pais)}
            valor={autoridadGobernanzaDigital}
            guardando={campoGuardando === "autoridad_gobernanza_digital"}
            error={campoConError === "autoridad_gobernanza_digital"}
            onCambiar={(valor) => {
              setAutoridadGobernanzaDigital(valor);
              guardarCampo("autoridad_gobernanza_digital", { autoridad_gobernanza_digital: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿El gobierno local publica la Agenda de Simplificación y Digitalización semestral?"
            ayuda={pais === "mx" ? "Obligación de la LNETB para todo sujeto obligado." : undefined}
            valor={agendaSimplificacionPublicada}
            guardando={campoGuardando === "agenda_simplificacion_publicada"}
            error={campoConError === "agenda_simplificacion_publicada"}
            onCambiar={(valor) => {
              setAgendaSimplificacionPublicada(valor);
              guardarCampo("agenda_simplificacion_publicada", { agenda_simplificacion_publicada: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿El gobierno local tiene un portal de datos abiertos?"
            valor={portalDatosAbiertosExiste}
            guardando={campoGuardando === "portal_datos_abiertos_existe"}
            error={campoConError === "portal_datos_abiertos_existe"}
            onCambiar={(valor) => {
              setPortalDatosAbiertosExiste(valor);
              guardarCampo("portal_datos_abiertos_existe", { portal_datos_abiertos_existe: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿Existe un canal único (línea telefónica, chat) de atención ciudadana para dudas sobre cualquier trámite?"
            valor={lineaAtencionCiudadanaCentralizada}
            guardando={campoGuardando === "linea_atencion_ciudadana_centralizada"}
            error={campoConError === "linea_atencion_ciudadana_centralizada"}
            onCambiar={(valor) => {
              setLineaAtencionCiudadanaCentralizada(valor);
              guardarCampo("linea_atencion_ciudadana_centralizada", { linea_atencion_ciudadana_centralizada: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿El personal que atiende trámites recibe al menos una capacitación digital al año?"
            valor={capacitacionPersonalTicAnual}
            guardando={campoGuardando === "capacitacion_personal_tic_anual"}
            error={campoConError === "capacitacion_personal_tic_anual"}
            onCambiar={(valor) => {
              setCapacitacionPersonalTicAnual(valor);
              guardarCampo("capacitacion_personal_tic_anual", { capacitacion_personal_tic_anual: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿Existe un protocolo formal de respuesta a incidentes de ciberseguridad?"
            valor={protocoloCiberseguridadExiste}
            guardando={campoGuardando === "protocolo_ciberseguridad_existe"}
            error={campoConError === "protocolo_ciberseguridad_existe"}
            onCambiar={(valor) => {
              setProtocoloCiberseguridadExiste(valor);
              guardarCampo("protocolo_ciberseguridad_existe", { protocolo_ciberseguridad_existe: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿El Enlace de Simplificación y Digitalización fue notificado formalmente ante la Autoridad Estatal/Nacional?"
            ayuda={pais === "mx" ? "LNETB art. 14." : undefined}
            valor={enlaceNotificadoFormalmente}
            guardando={campoGuardando === "enlace_notificado_formalmente"}
            error={campoConError === "enlace_notificado_formalmente"}
            onCambiar={(valor) => {
              setEnlaceNotificadoFormalmente(valor);
              guardarCampo("enlace_notificado_formalmente", { enlace_notificado_formalmente: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿Existe un convenio de colaboración vigente con el estado/Autoridad Nacional en materia de digitalización?"
            ayuda={pais === "mx" ? "LNETB art. 25." : undefined}
            valor={convenioColaboracionEstado}
            guardando={campoGuardando === "convenio_colaboracion_estado"}
            error={campoConError === "convenio_colaboracion_estado"}
            onCambiar={(valor) => {
              setConvenioColaboracionEstado(valor);
              guardarCampo("convenio_colaboracion_estado", { convenio_colaboracion_estado: valor });
            }}
          />
          <CampoSelect
            id="infraestructura_firma_electronica"
            etiqueta="¿Cómo está resuelta la infraestructura de firma electrónica avanzada del gobierno local?"
            opciones={INFRAESTRUCTURA_FIRMA_ELECTRONICA_OPCIONES}
            valor={infraestructuraFirmaElectronica}
            guardando={campoGuardando === "infraestructura_firma_electronica"}
            error={campoConError === "infraestructura_firma_electronica"}
            onCambiar={(valor) => {
              setInfraestructuraFirmaElectronica(valor);
              guardarCampo("infraestructura_firma_electronica", { infraestructura_firma_electronica: valor });
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Madurez digital transversal</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <CampoPorcentajeConBandera
            etiqueta="¿Qué porcentaje del catálogo total de trámites puede iniciarse y concluirse 100% en línea (incluyendo pago y entrega del resultado)?"
            textoBandera="No se mide"
            valorInicial={porcentajeTramitesEnLinea}
            bandera={porcentajeTramitesEnLineaNoSeMide}
            guardando={campoGuardando === "porcentaje_tramites_en_linea"}
            error={campoConError === "porcentaje_tramites_en_linea"}
            onGuardarValor={(valor) => {
              setPorcentajeTramitesEnLinea(String(valor));
              guardarCampo("porcentaje_tramites_en_linea", { porcentaje_tramites_en_linea: valor });
            }}
            onCambiarBandera={(valor) => {
              setPorcentajeTramitesEnLineaNoSeMide(valor);
              guardarCampo("porcentaje_tramites_en_linea_no_se_mide", {
                porcentaje_tramites_en_linea_no_se_mide: valor,
              });
            }}
          />
          <CampoSelect
            id="portal_tramites_tipo"
            etiqueta="¿El gobierno cuenta con un portal o aplicación única de trámites, o cada dependencia tiene su propia página?"
            opciones={PORTAL_TRAMITES_OPCIONES}
            valor={portalTramitesTipo}
            guardando={campoGuardando === "portal_tramites_tipo"}
            error={campoConError === "portal_tramites_tipo"}
            onCambiar={(valor) => {
              setPortalTramitesTipo(valor);
              guardarCampo("portal_tramites_tipo", { portal_tramites_tipo: valor });
            }}
          />
          <CampoSelect
            id="pagos_electronicos_generalizados"
            etiqueta="¿El gobierno acepta pagos electrónicos (tarjeta, transferencia, billeteras digitales) de forma general para sus trámites?"
            opciones={SI_NO_SOLO_ALGUNOS_OPCIONES}
            valor={pagosElectronicosGeneralizados}
            guardando={campoGuardando === "pagos_electronicos_generalizados"}
            error={campoConError === "pagos_electronicos_generalizados"}
            onCambiar={(valor) => {
              setPagosElectronicosGeneralizados(valor);
              guardarCampo("pagos_electronicos_generalizados", { pagos_electronicos_generalizados: valor });
            }}
          />
          <CampoSelect
            id="mecanismo_identidad_estandar"
            etiqueta="¿Qué mecanismo de identidad digital utiliza el gobierno como estándar para sus trámites en línea?"
            ayuda="Si varía por trámite, es señal de que no hay un estándar institucional."
            opciones={MECANISMO_IDENTIDAD_ESTANDAR_OPCIONES}
            valor={mecanismoIdentidadEstandar}
            guardando={campoGuardando === "mecanismo_identidad_estandar"}
            error={campoConError === "mecanismo_identidad_estandar"}
            onCambiar={(valor) => {
              setMecanismoIdentidadEstandar(valor);
              guardarCampo("mecanismo_identidad_estandar", { mecanismo_identidad_estandar: valor });
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Interoperabilidad y gobierno de datos</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <CampoSelect
            id="interoperabilidad_entre_areas"
            etiqueta="¿Las distintas áreas del gobierno (catastro, tesorería, padrón, recursos humanos, etc.) comparten información entre sí de forma automatizada?"
            opciones={SI_NO_PARCIALMENTE_OPCIONES}
            valor={interoperabilidadEntreAreas}
            guardando={campoGuardando === "interoperabilidad_entre_areas"}
            error={campoConError === "interoperabilidad_entre_areas"}
            onCambiar={(valor) => {
              setInteroperabilidadEntreAreas(valor);
              guardarCampo("interoperabilidad_entre_areas", { interoperabilidad_entre_areas: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿Existe un inventario o catálogo actualizado de los sistemas de información que usa el gobierno?"
            valor={inventarioSistemasExiste}
            guardando={campoGuardando === "inventario_sistemas_existe"}
            error={campoConError === "inventario_sistemas_existe"}
            onCambiar={(valor) => {
              setInventarioSistemasExiste(valor);
              guardarCampo("inventario_sistemas_existe", { inventario_sistemas_existe: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿El gobierno tiene alguna política o lineamiento formal de gobierno de datos (calidad, resguardo, interoperabilidad)?"
            valor={politicaGobiernoDatosExiste}
            guardando={campoGuardando === "politica_gobierno_datos_existe"}
            error={campoConError === "politica_gobierno_datos_existe"}
            onCambiar={(valor) => {
              setPoliticaGobiernoDatosExiste(valor);
              guardarCampo("politica_gobierno_datos_existe", { politica_gobierno_datos_existe: valor });
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ciberseguridad</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <CampoBooleano
            pregunta="¿El gobierno realiza respaldos (backups) periódicos de su información crítica?"
            valor={respaldosPeriodicosExisten}
            guardando={campoGuardando === "respaldos_periodicos_existen"}
            error={campoConError === "respaldos_periodicos_existen"}
            onCambiar={(valor) => {
              setRespaldosPeriodicosExisten(valor);
              guardarCampo("respaldos_periodicos_existen", { respaldos_periodicos_existen: valor });
            }}
          />
          <CampoSelect
            id="incidente_ciberseguridad_24meses"
            etiqueta="¿El gobierno ha sufrido algún incidente de ciberseguridad (brecha de datos, ransomware, caída de sistemas) en los últimos 24 meses?"
            opciones={INCIDENTE_CIBERSEGURIDAD_OPCIONES}
            valor={incidenteCiberseguridad24meses}
            guardando={campoGuardando === "incidente_ciberseguridad_24meses"}
            error={campoConError === "incidente_ciberseguridad_24meses"}
            onCambiar={(valor) => {
              setIncidenteCiberseguridad24meses(valor);
              guardarCampo("incidente_ciberseguridad_24meses", { incidente_ciberseguridad_24meses: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿Cuenta con alguna certificación o auditoría externa de seguridad de la información (ISO 27001 u otra)?"
            valor={certificacionSeguridadExterna}
            guardando={campoGuardando === "certificacion_seguridad_externa"}
            error={campoConError === "certificacion_seguridad_externa"}
            onCambiar={(valor) => {
              setCertificacionSeguridadExterna(valor);
              guardarCampo("certificacion_seguridad_externa", { certificacion_seguridad_externa: valor });
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Capital humano de TI</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <CampoSelect
            id="rotacion_personal_ti"
            etiqueta="¿Cuál es la rotación anual aproximada del personal del área de TI?"
            ayuda="La alta rotación es un problema crónico en gobiernos locales y limita la continuidad de cualquier proyecto de digitalización."
            opciones={ROTACION_PERSONAL_TI_OPCIONES}
            valor={rotacionPersonalTi}
            guardando={campoGuardando === "rotacion_personal_ti"}
            error={campoConError === "rotacion_personal_ti"}
            onCambiar={(valor) => {
              setRotacionPersonalTi(valor);
              guardarCampo("rotacion_personal_ti", { rotacion_personal_ti: valor });
            }}
          />
          <CampoSelect
            id="dependencia_outsourcing_ti"
            etiqueta="¿El gobierno depende de outsourcing o proveedores externos para operar sus sistemas críticos?"
            opciones={DEPENDENCIA_OUTSOURCING_OPCIONES}
            valor={dependenciaOutsourcingTi}
            guardando={campoGuardando === "dependencia_outsourcing_ti"}
            error={campoConError === "dependencia_outsourcing_ti"}
            onCambiar={(valor) => {
              setDependenciaOutsourcingTi(valor);
              guardarCampo("dependencia_outsourcing_ti", { dependencia_outsourcing_ti: valor });
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Medición y evaluación</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <CampoBooleano
            pregunta="¿El gobierno mide de forma sistemática los tiempos de resolución de sus trámites?"
            valor={mideTiemposResolucion}
            guardando={campoGuardando === "mide_tiempos_resolucion"}
            error={campoConError === "mide_tiempos_resolucion"}
            onCambiar={(valor) => {
              setMideTiemposResolucion(valor);
              guardarCampo("mide_tiempos_resolucion", { mide_tiempos_resolucion: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿El gobierno mide la satisfacción ciudadana con sus trámites y servicios?"
            valor={mideSatisfaccionCiudadana}
            guardando={campoGuardando === "mide_satisfaccion_ciudadana"}
            error={campoConError === "mide_satisfaccion_ciudadana"}
            onCambiar={(valor) => {
              setMideSatisfaccionCiudadana(valor);
              guardarCampo("mide_satisfaccion_ciudadana", { mide_satisfaccion_ciudadana: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿Existe algún tablero o reporte de indicadores de desempeño de trámites (interno o público)?"
            valor={tableroIndicadoresExiste}
            guardando={campoGuardando === "tablero_indicadores_existe"}
            error={campoConError === "tablero_indicadores_existe"}
            onCambiar={(valor) => {
              setTableroIndicadoresExiste(valor);
              guardarCampo("tablero_indicadores_existe", { tablero_indicadores_existe: valor });
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Financiamiento para digitalización</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <CampoBooleano
            pregunta="¿El gobierno ha recibido o gestionado fondos estatales/federales etiquetados específicamente para digitalización en los últimos 3 años?"
            valor={fondosDigitalizacionRecibidos}
            guardando={campoGuardando === "fondos_digitalizacion_recibidos"}
            error={campoConError === "fondos_digitalizacion_recibidos"}
            onCambiar={(valor) => {
              setFondosDigitalizacionRecibidos(valor);
              guardarCampo("fondos_digitalizacion_recibidos", { fondos_digitalizacion_recibidos: valor });
            }}
          />
          {fondosDigitalizacionRecibidos === true && (
            <div className="flex flex-col gap-1.5">
              <label htmlFor="fondos_detalle" className="text-sm font-medium">
                ¿Monto aproximado y fuente?
              </label>
              <Textarea
                id="fondos_detalle"
                value={fondosDigitalizacionDetalle}
                onChange={(e) => setFondosDigitalizacionDetalle(e.target.value)}
                onBlur={() =>
                  guardarCampo("fondos_digitalizacion_detalle", {
                    fondos_digitalizacion_detalle: fondosDigitalizacionDetalle,
                  })
                }
                rows={2}
              />
              <EstadoGuardado
                guardando={campoGuardando === "fondos_digitalizacion_detalle"}
                error={campoConError === "fondos_digitalizacion_detalle"}
              />
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Accesibilidad e inclusión digital</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <CampoPorcentajeConBandera
            etiqueta="¿Qué porcentaje aproximado de la población del municipio/gobierno local tiene acceso a internet o smartphone?"
            textoBandera="No se tiene el dato"
            ayuda="Contextualiza si digitalizar un trámite tiene sentido de adopción real para la población que lo usa."
            valorInicial={porcentajePoblacionAccesoInternet}
            bandera={porcentajePoblacionAccesoInternetNoSeTieneDato}
            guardando={campoGuardando === "porcentaje_poblacion_acceso_internet"}
            error={campoConError === "porcentaje_poblacion_acceso_internet"}
            onGuardarValor={(valor) => {
              setPorcentajePoblacionAccesoInternet(String(valor));
              guardarCampo("porcentaje_poblacion_acceso_internet", { porcentaje_poblacion_acceso_internet: valor });
            }}
            onCambiarBandera={(valor) => {
              setPorcentajePoblacionAccesoInternetNoSeTieneDato(valor);
              guardarCampo("porcentaje_poblacion_acceso_internet_no_se_tiene_dato", {
                porcentaje_poblacion_acceso_internet_no_se_tiene_dato: valor,
              });
            }}
          />
          <CampoSelect
            id="accesibilidad_sistemas_discapacidad"
            etiqueta="¿Los sistemas o portales digitales del gobierno cumplen, en general, con estándares de accesibilidad para personas con discapacidad?"
            opciones={SI_NO_PARCIALMENTE_OPCIONES}
            valor={accesibilidadSistemasDiscapacidad}
            guardando={campoGuardando === "accesibilidad_sistemas_discapacidad"}
            error={campoConError === "accesibilidad_sistemas_discapacidad"}
            onCambiar={(valor) => {
              setAccesibilidadSistemasDiscapacidad(valor);
              guardarCampo("accesibilidad_sistemas_discapacidad", { accesibilidad_sistemas_discapacidad: valor });
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Catálogo y transparencia de trámites</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <CampoBooleano
            pregunta="¿El gobierno cuenta con un Registro o Catálogo de Trámites y Servicios público y actualizado?"
            ayuda="Distinto del Portal Ciudadano Único (que puede ser federal/estatal) -- aquí se pregunta si el propio gobierno local mantiene su catálogo interno actualizado."
            valor={catalogoTramitesPropioExiste}
            guardando={campoGuardando === "catalogo_tramites_propio_existe"}
            error={campoConError === "catalogo_tramites_propio_existe"}
            onCambiar={(valor) => {
              setCatalogoTramitesPropioExiste(valor);
              guardarCampo("catalogo_tramites_propio_existe", { catalogo_tramites_propio_existe: valor });
            }}
          />
        </CardContent>
      </Card>
    </div>
  );
}

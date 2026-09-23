import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { CampoBooleanoRadio } from "@/components/ui/campo-booleano-radio";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useAutoguardadoCampo } from "@/hooks/useAutoguardadoCampo";
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
import { subirLogoGobierno } from "@/lib/logoGobiernoApi";
import { esAdmin, obtenerPais } from "@/lib/session";
import { useLogoGobiernoUrl } from "@/lib/useLogoGobierno";

// Perfil del gobierno: variables de contexto capturadas una sola vez por tenant.
// Sin "enviar cuestionario completo" -- cada campo se autoguarda al confirmarse
// (RadioGroup/Select al elegir, numéricos en onBlur), vía useAutoguardadoCampo
// con debounceMs=0 (async, no bloquea el evento, solo centraliza el estado).

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
  // pais aún no resuelto (token viejo sin el claim) -- pregunta neutra en vez
  // de citar la norma de un país que puede no corresponder.
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
  onGuardar,
}: {
  pregunta: string;
  ayuda?: string;
  valor: boolean | null;
  onGuardar: (valor: boolean) => Promise<unknown>;
}) {
  const id = pregunta.slice(0, 20);
  const [valorLocal, setValorLocal] = useState(valor);
  useEffect(() => setValorLocal(valor), [valor]);
  const estado = useAutoguardadoCampo(valorLocal, (v) => (v === null ? Promise.resolve() : onGuardar(v)), 0);

  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-medium">{pregunta}</p>
      <CampoBooleanoRadio valor={valorLocal} onCambiar={setValorLocal} idPrefix={id} />
      {ayuda && <p className="text-xs text-atenuado">{ayuda}</p>}
      <EstadoGuardado guardando={estado === "guardando"} error={estado === "error"} />
    </div>
  );
}

// Un valor fuera de rango (`min`/`max`) muestra error junto al campo y nunca se
// guarda en silencio -- antes se descartaba sin avisar (QA ronda 2, hallazgo #5).
function CampoNumerico({
  etiqueta,
  ayuda,
  valorInicial,
  min = 0,
  max,
  onGuardar,
}: {
  etiqueta: string;
  ayuda?: string;
  valorInicial: string;
  min?: number;
  max?: number;
  onGuardar: (valor: number) => Promise<unknown>;
}) {
  const [valor, setValor] = useState(valorInicial);
  const [errorValidacion, setErrorValidacion] = useState<string | null>(null);
  // El hook observa este valor confirmado (onBlur), no el buffer de arriba --
  // nunca autoguarda mientras el funcionario sigue escribiendo.
  const [valorConfirmado, setValorConfirmado] = useState(valorInicial);

  useEffect(() => {
    setValor(valorInicial);
    setValorConfirmado(valorInicial);
    setErrorValidacion(null);
  }, [valorInicial]);

  const estado = useAutoguardadoCampo(valorConfirmado, (v) => onGuardar(Number(v)), 0);

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
          if (valor.trim() === "" || valor === valorConfirmado) return;
          const numero = Number(valor);
          const mensaje = validar(numero);
          if (mensaje) {
            setErrorValidacion(mensaje);
            return;
          }
          setValorConfirmado(valor);
        }}
        className="sm:w-64"
      />
      {ayuda && <p className="text-xs text-atenuado">{ayuda}</p>}
      {errorValidacion && <p className="text-xs text-destructive">{errorValidacion}</p>}
      <EstadoGuardado guardando={estado === "guardando"} error={estado === "error"} />
    </div>
  );
}

function CampoConectividad({
  valor,
  onGuardar,
}: {
  valor: Conectividad | null;
  onGuardar: (valor: Conectividad) => Promise<unknown>;
}) {
  const [valorLocal, setValorLocal] = useState(valor);
  useEffect(() => setValorLocal(valor), [valor]);
  const estado = useAutoguardadoCampo(valorLocal, (v) => (v === null ? Promise.resolve() : onGuardar(v)), 0);

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor="conectividad" className="text-sm font-medium">
        ¿Cómo describiría la conectividad a internet de las oficinas donde se atienden trámites?
      </label>
      <select
        id="conectividad"
        value={valorLocal ?? ""}
        onChange={(e) => setValorLocal(e.target.value as Conectividad)}
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
      <EstadoGuardado guardando={estado === "guardando"} error={estado === "error"} />
    </div>
  );
}

// Genérico -- reemplaza los ~8 selects casi idénticos que necesita este perfil.
function CampoSelect<T extends string>({
  id,
  etiqueta,
  ayuda,
  opciones,
  valor,
  onGuardar,
}: {
  id: string;
  etiqueta: string;
  ayuda?: string;
  opciones: { valor: T; etiqueta: string }[];
  valor: T | null;
  onGuardar: (valor: T) => Promise<unknown>;
}) {
  const [valorLocal, setValorLocal] = useState(valor);
  useEffect(() => setValorLocal(valor), [valor]);
  const estado = useAutoguardadoCampo(valorLocal, (v) => (v === null ? Promise.resolve() : onGuardar(v)), 0);

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-sm font-medium">
        {etiqueta}
      </label>
      <select
        id={id}
        value={valorLocal ?? ""}
        onChange={(e) => setValorLocal(e.target.value as T)}
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
      <EstadoGuardado guardando={estado === "guardando"} error={estado === "error"} />
    </div>
  );
}

// Número 0-100 + casilla "no se mide" -- respuesta explícita, distinta de
// "todavía no se llenó". Valor y bandera son campos independientes en el
// backend, cada uno con su propio useAutoguardadoCampo.
function CampoPorcentajeConBandera({
  etiqueta,
  textoBandera,
  ayuda,
  valorInicial,
  bandera,
  onGuardarValor,
  onGuardarBandera,
}: {
  etiqueta: string;
  textoBandera: string;
  ayuda?: string;
  valorInicial: string;
  bandera: boolean;
  onGuardarValor: (valor: number) => Promise<unknown>;
  onGuardarBandera: (valor: boolean) => Promise<unknown>;
}) {
  const [valor, setValor] = useState(valorInicial);
  const [errorValidacion, setErrorValidacion] = useState<string | null>(null);
  const [valorConfirmado, setValorConfirmado] = useState(valorInicial);
  const [banderaLocal, setBanderaLocal] = useState(bandera);

  useEffect(() => {
    setValor(valorInicial);
    setValorConfirmado(valorInicial);
    setErrorValidacion(null);
  }, [valorInicial]);

  useEffect(() => setBanderaLocal(bandera), [bandera]);

  const estadoValor = useAutoguardadoCampo(valorConfirmado, (v) => onGuardarValor(Number(v)), 0);
  const estadoBandera = useAutoguardadoCampo(banderaLocal, onGuardarBandera, 0);
  const guardando = estadoValor === "guardando" || estadoBandera === "guardando";
  const conError = estadoValor === "error" || estadoBandera === "error";

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
              // Mismo criterio que CampoNumerico: nunca descartar en silencio.
              if (valor.trim() === "" || valor === valorConfirmado) return;
              const numero = Number(valor);
              if (!Number.isFinite(numero)) {
                setErrorValidacion("Escribe un número válido.");
                return;
              }
              if (numero < 0 || numero > 100) {
                setErrorValidacion("Escribe un número de 0 a 100.");
                return;
              }
              setValorConfirmado(valor);
            }}
            className="sm:w-64"
          />
          {errorValidacion && <p className="text-xs text-destructive">{errorValidacion}</p>}
        </>
      )}
      <label className="flex items-center gap-2 text-xs text-atenuado">
        <input type="checkbox" checked={banderaLocal} onChange={(e) => setBanderaLocal(e.target.checked)} />
        {textoBandera}
      </label>
      {ayuda && <p className="text-xs text-atenuado">{ayuda}</p>}
      <EstadoGuardado guardando={guardando} error={conError} />
    </div>
  );
}

// Único campo de texto libre del perfil -- mismo patrón "confirmado en blur"
// que CampoNumerico, sin validación numérica.
function CampoTextoConfirmado({
  id,
  etiqueta,
  valor,
  onGuardar,
}: {
  id: string;
  etiqueta: string;
  valor: string;
  onGuardar: (valor: string) => Promise<unknown>;
}) {
  const [texto, setTexto] = useState(valor);
  const [confirmado, setConfirmado] = useState(valor);

  useEffect(() => {
    setTexto(valor);
    setConfirmado(valor);
  }, [valor]);

  const estado = useAutoguardadoCampo(confirmado, onGuardar, 0);

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {etiqueta}
      </label>
      <Textarea id={id} value={texto} onChange={(e) => setTexto(e.target.value)} onBlur={() => setConfirmado(texto)} rows={2} />
      <EstadoGuardado guardando={estado === "guardando"} error={estado === "error"} />
    </div>
  );
}

// Logo del gobierno: GET abierto a cualquier funcionario, PUT solo
// admin_gobierno -- el control se oculta a quien no puede usarlo.
function TarjetaLogoGobierno() {
  const queryClient = useQueryClient();
  const logoUrl = useLogoGobiernoUrl();
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const subirMutacion = useMutation({
    mutationFn: subirLogoGobierno,
    onSuccess: () => {
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["logo-gobierno"] });
    },
    onError: (err: unknown) => {
      setError(err instanceof Error ? err.message : "No se pudo subir el logo.");
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Logo del gobierno</CardTitle>
      </CardHeader>
      <CardContent className="flex items-center gap-4">
        <div className="flex size-16 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-border bg-muted">
          {logoUrl ? (
            <img src={logoUrl} alt="" className="size-full object-cover" />
          ) : (
            <span className="text-xs text-atenuado">Sin logo</span>
          )}
        </div>
        <div className="flex flex-col gap-1.5">
          <p className="text-sm text-muted-foreground">
            Aparece junto al nombre del gobierno en la barra superior y como marca de agua en el Panel resumen.
          </p>
          {esAdmin() && (
            <>
              <input
                ref={inputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp,image/svg+xml"
                className="hidden"
                onChange={(e) => {
                  const archivo = e.target.files?.[0];
                  e.target.value = "";
                  if (archivo) subirMutacion.mutate(archivo);
                }}
              />
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="w-fit"
                disabled={subirMutacion.isPending}
                onClick={() => inputRef.current?.click()}
              >
                {subirMutacion.isPending ? "Subiendo..." : logoUrl ? "Reemplazar logo" : "Subir logo"}
              </Button>
              {error && (
                <p role="alert" className="text-xs text-destructive">
                  {error}
                </p>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function GobiernoPerfil() {
  const pais = obtenerPais();
  const queryClient = useQueryClient();
  const inicializadoRef = useRef(false);

  const [poblacionTotal, setPoblacionTotal] = useState("");
  // Badge "Fuente: INEGI" solo si vino de la sincronización, no si se escribió a mano.
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

  // Madurez digital transversal, ciberseguridad, capital humano de TI, accesibilidad.
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

  const contextoQuery = useQuery({
    queryKey: ["gobierno-contexto"],
    queryFn: obtenerContextoInstitucional,
  });

  // Aplica los datos del servidor a todos los campos -- al cargar y tras cada
  // guardado exitoso, para no quedar desincronizado si otro campo cambió el
  // dato por su cuenta (ej. sincronización con INEGI).
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

  // Única mutación de guardado -- cada campo la invoca vía `mutateAsync` (el
  // hook necesita la Promise para su propio "Guardando…"/error).
  const guardarMutacion = useMutation({
    mutationFn: (payload: ContextoInstitucionalPayload) => guardarContextoInstitucional(payload),
    onSuccess: (respuesta: ContextoInstitucionalResponse) => {
      queryClient.setQueryData(["gobierno-contexto"], respuesta);
      aplicarDatos(respuesta);
    },
  });

  // Trae `poblacion_total` real de INEGI. El backend ya devuelve un 422 con
  // `detail` en lenguaje llano listo para mostrar tal cual.
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

      <TarjetaLogoGobierno />

      <Card>
        <CardHeader>
          <CardTitle>Contexto</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <CampoNumerico
            etiqueta="¿Cuál es la población total del gobierno local (último dato oficial disponible)?"
            valorInicial={poblacionTotal}
            onGuardar={(valor) => {
              setPoblacionTotal(String(valor));
              return guardarMutacion.mutateAsync({ poblacion_total: valor });
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
            onGuardar={(valor) => {
              setPersonalTotalGobierno(String(valor));
              return guardarMutacion.mutateAsync({ personal_total_gobierno: valor });
            }}
          />
          <CampoNumerico
            etiqueta="¿Cuál es el presupuesto anual destinado a tecnologías de la información del gobierno local?"
            ayuda={pais === "uy" ? "Monto en UYU" : "Monto en MXN"}
            valorInicial={presupuestoTicAnual}
            onGuardar={(valor) => {
              setPresupuestoTicAnual(String(valor));
              return guardarMutacion.mutateAsync({ presupuesto_tic_anual: valor });
            }}
          />
          <CampoNumerico
            etiqueta="¿Cuál es el presupuesto TOTAL anual del gobierno local (no solo TIC)?"
            ayuda={pais === "uy" ? "Monto en UYU -- da contexto de qué tan grande es el presupuesto de TIC en comparación" : "Monto en MXN -- da contexto de qué tan grande es el presupuesto de TIC en comparación"}
            valorInicial={presupuestoTotalAnual}
            onGuardar={(valor) => {
              setPresupuestoTotalAnual(String(valor));
              return guardarMutacion.mutateAsync({ presupuesto_total_anual: valor });
            }}
          />
          <CampoNumerico
            etiqueta="¿Cuántos trámites en total ofrece el gobierno local (no solo los ya diagnosticados aquí)?"
            valorInicial={numeroTramitesTotales}
            onGuardar={(valor) => {
              setNumeroTramitesTotales(String(valor));
              return guardarMutacion.mutateAsync({ numero_tramites_totales: valor });
            }}
          />
          <CampoNumerico
            etiqueta="¿Qué porcentaje de los ingresos del gobierno son propios (no participaciones ni transferencias)?"
            ayuda="Un número de 0 a 100."
            valorInicial={ingresosPropiosPorcentaje}
            max={100}
            onGuardar={(valor) => {
              setIngresosPropiosPorcentaje(String(valor));
              return guardarMutacion.mutateAsync({ ingresos_propios_porcentaje: valor });
            }}
          />
          <CampoNumerico
            etiqueta="¿Cuántas oficinas o ventanillas físicas de atención al público tiene el gobierno local?"
            valorInicial={numeroOficinasAtencion}
            onGuardar={(valor) => {
              setNumeroOficinasAtencion(String(valor));
              return guardarMutacion.mutateAsync({ numero_oficinas_atencion: valor });
            }}
          />
          <CampoNumerico
            etiqueta="¿Cuántas personas conforman el área de TI del gobierno local?"
            ayuda="Distinto del personal total del gobierno de arriba -- solo el área de TI."
            valorInicial={personalAreaTi}
            onGuardar={(valor) => {
              setPersonalAreaTi(String(valor));
              return guardarMutacion.mutateAsync({ personal_area_ti: valor });
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
            onGuardar={(valor) => {
              setAreaTicExiste(valor);
              return guardarMutacion.mutateAsync({ area_tic_existe: valor });
            }}
          />
          <CampoConectividad
            valor={conectividad}
            onGuardar={(valor) => {
              setConectividad(valor);
              return guardarMutacion.mutateAsync({ conectividad: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿El gobierno local ha emitido normativa propia de simplificación o digitalización (reglamento, decreto o resolución municipal/departamental)?"
            valor={normativaLocalEmitida}
            onGuardar={(valor) => {
              setNormativaLocalEmitida(valor);
              return guardarMutacion.mutateAsync({ normativa_local_emitida: valor });
            }}
          />
          <CampoBooleano
            pregunta={preguntaAutoridadGobernanza(pais)}
            valor={autoridadGobernanzaDigital}
            onGuardar={(valor) => {
              setAutoridadGobernanzaDigital(valor);
              return guardarMutacion.mutateAsync({ autoridad_gobernanza_digital: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿El gobierno local publica la Agenda de Simplificación y Digitalización semestral?"
            ayuda={pais === "mx" ? "Obligación de la LNETB para todo sujeto obligado." : undefined}
            valor={agendaSimplificacionPublicada}
            onGuardar={(valor) => {
              setAgendaSimplificacionPublicada(valor);
              return guardarMutacion.mutateAsync({ agenda_simplificacion_publicada: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿El gobierno local tiene un portal de datos abiertos?"
            valor={portalDatosAbiertosExiste}
            onGuardar={(valor) => {
              setPortalDatosAbiertosExiste(valor);
              return guardarMutacion.mutateAsync({ portal_datos_abiertos_existe: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿Existe un canal único (línea telefónica, chat) de atención ciudadana para dudas sobre cualquier trámite?"
            valor={lineaAtencionCiudadanaCentralizada}
            onGuardar={(valor) => {
              setLineaAtencionCiudadanaCentralizada(valor);
              return guardarMutacion.mutateAsync({ linea_atencion_ciudadana_centralizada: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿El personal que atiende trámites recibe al menos una capacitación digital al año?"
            valor={capacitacionPersonalTicAnual}
            onGuardar={(valor) => {
              setCapacitacionPersonalTicAnual(valor);
              return guardarMutacion.mutateAsync({ capacitacion_personal_tic_anual: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿Existe un protocolo formal de respuesta a incidentes de ciberseguridad?"
            valor={protocoloCiberseguridadExiste}
            onGuardar={(valor) => {
              setProtocoloCiberseguridadExiste(valor);
              return guardarMutacion.mutateAsync({ protocolo_ciberseguridad_existe: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿El Enlace de Simplificación y Digitalización fue notificado formalmente ante la Autoridad Estatal/Nacional?"
            ayuda={pais === "mx" ? "LNETB art. 14." : undefined}
            valor={enlaceNotificadoFormalmente}
            onGuardar={(valor) => {
              setEnlaceNotificadoFormalmente(valor);
              return guardarMutacion.mutateAsync({ enlace_notificado_formalmente: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿Existe un convenio de colaboración vigente con el estado/Autoridad Nacional en materia de digitalización?"
            ayuda={pais === "mx" ? "LNETB art. 25." : undefined}
            valor={convenioColaboracionEstado}
            onGuardar={(valor) => {
              setConvenioColaboracionEstado(valor);
              return guardarMutacion.mutateAsync({ convenio_colaboracion_estado: valor });
            }}
          />
          <CampoSelect
            id="infraestructura_firma_electronica"
            etiqueta="¿Cómo está resuelta la infraestructura de firma electrónica avanzada del gobierno local?"
            opciones={INFRAESTRUCTURA_FIRMA_ELECTRONICA_OPCIONES}
            valor={infraestructuraFirmaElectronica}
            onGuardar={(valor) => {
              setInfraestructuraFirmaElectronica(valor);
              return guardarMutacion.mutateAsync({ infraestructura_firma_electronica: valor });
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
            onGuardarValor={(valor) => {
              setPorcentajeTramitesEnLinea(String(valor));
              return guardarMutacion.mutateAsync({ porcentaje_tramites_en_linea: valor });
            }}
            onGuardarBandera={(valor) => {
              setPorcentajeTramitesEnLineaNoSeMide(valor);
              return guardarMutacion.mutateAsync({ porcentaje_tramites_en_linea_no_se_mide: valor });
            }}
          />
          <CampoSelect
            id="portal_tramites_tipo"
            etiqueta="¿El gobierno cuenta con un portal o aplicación única de trámites, o cada dependencia tiene su propia página?"
            opciones={PORTAL_TRAMITES_OPCIONES}
            valor={portalTramitesTipo}
            onGuardar={(valor) => {
              setPortalTramitesTipo(valor);
              return guardarMutacion.mutateAsync({ portal_tramites_tipo: valor });
            }}
          />
          <CampoSelect
            id="pagos_electronicos_generalizados"
            etiqueta="¿El gobierno acepta pagos electrónicos (tarjeta, transferencia, billeteras digitales) de forma general para sus trámites?"
            opciones={SI_NO_SOLO_ALGUNOS_OPCIONES}
            valor={pagosElectronicosGeneralizados}
            onGuardar={(valor) => {
              setPagosElectronicosGeneralizados(valor);
              return guardarMutacion.mutateAsync({ pagos_electronicos_generalizados: valor });
            }}
          />
          <CampoSelect
            id="mecanismo_identidad_estandar"
            etiqueta="¿Qué mecanismo de identidad digital utiliza el gobierno como estándar para sus trámites en línea?"
            ayuda="Si varía por trámite, es señal de que no hay un estándar institucional."
            opciones={MECANISMO_IDENTIDAD_ESTANDAR_OPCIONES}
            valor={mecanismoIdentidadEstandar}
            onGuardar={(valor) => {
              setMecanismoIdentidadEstandar(valor);
              return guardarMutacion.mutateAsync({ mecanismo_identidad_estandar: valor });
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
            onGuardar={(valor) => {
              setInteroperabilidadEntreAreas(valor);
              return guardarMutacion.mutateAsync({ interoperabilidad_entre_areas: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿Existe un inventario o catálogo actualizado de los sistemas de información que usa el gobierno?"
            valor={inventarioSistemasExiste}
            onGuardar={(valor) => {
              setInventarioSistemasExiste(valor);
              return guardarMutacion.mutateAsync({ inventario_sistemas_existe: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿El gobierno tiene alguna política o lineamiento formal de gobierno de datos (calidad, resguardo, interoperabilidad)?"
            valor={politicaGobiernoDatosExiste}
            onGuardar={(valor) => {
              setPoliticaGobiernoDatosExiste(valor);
              return guardarMutacion.mutateAsync({ politica_gobierno_datos_existe: valor });
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
            onGuardar={(valor) => {
              setRespaldosPeriodicosExisten(valor);
              return guardarMutacion.mutateAsync({ respaldos_periodicos_existen: valor });
            }}
          />
          <CampoSelect
            id="incidente_ciberseguridad_24meses"
            etiqueta="¿El gobierno ha sufrido algún incidente de ciberseguridad (brecha de datos, ransomware, caída de sistemas) en los últimos 24 meses?"
            opciones={INCIDENTE_CIBERSEGURIDAD_OPCIONES}
            valor={incidenteCiberseguridad24meses}
            onGuardar={(valor) => {
              setIncidenteCiberseguridad24meses(valor);
              return guardarMutacion.mutateAsync({ incidente_ciberseguridad_24meses: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿Cuenta con alguna certificación o auditoría externa de seguridad de la información (ISO 27001 u otra)?"
            valor={certificacionSeguridadExterna}
            onGuardar={(valor) => {
              setCertificacionSeguridadExterna(valor);
              return guardarMutacion.mutateAsync({ certificacion_seguridad_externa: valor });
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
            onGuardar={(valor) => {
              setRotacionPersonalTi(valor);
              return guardarMutacion.mutateAsync({ rotacion_personal_ti: valor });
            }}
          />
          <CampoSelect
            id="dependencia_outsourcing_ti"
            etiqueta="¿El gobierno depende de outsourcing o proveedores externos para operar sus sistemas críticos?"
            opciones={DEPENDENCIA_OUTSOURCING_OPCIONES}
            valor={dependenciaOutsourcingTi}
            onGuardar={(valor) => {
              setDependenciaOutsourcingTi(valor);
              return guardarMutacion.mutateAsync({ dependencia_outsourcing_ti: valor });
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
            onGuardar={(valor) => {
              setMideTiemposResolucion(valor);
              return guardarMutacion.mutateAsync({ mide_tiempos_resolucion: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿El gobierno mide la satisfacción ciudadana con sus trámites y servicios?"
            valor={mideSatisfaccionCiudadana}
            onGuardar={(valor) => {
              setMideSatisfaccionCiudadana(valor);
              return guardarMutacion.mutateAsync({ mide_satisfaccion_ciudadana: valor });
            }}
          />
          <CampoBooleano
            pregunta="¿Existe algún tablero o reporte de indicadores de desempeño de trámites (interno o público)?"
            valor={tableroIndicadoresExiste}
            onGuardar={(valor) => {
              setTableroIndicadoresExiste(valor);
              return guardarMutacion.mutateAsync({ tablero_indicadores_existe: valor });
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
            onGuardar={(valor) => {
              setFondosDigitalizacionRecibidos(valor);
              return guardarMutacion.mutateAsync({ fondos_digitalizacion_recibidos: valor });
            }}
          />
          {fondosDigitalizacionRecibidos === true && (
            <CampoTextoConfirmado
              id="fondos_detalle"
              etiqueta="¿Monto aproximado y fuente?"
              valor={fondosDigitalizacionDetalle}
              onGuardar={(valor) => {
                setFondosDigitalizacionDetalle(valor);
                return guardarMutacion.mutateAsync({ fondos_digitalizacion_detalle: valor });
              }}
            />
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
            onGuardarValor={(valor) => {
              setPorcentajePoblacionAccesoInternet(String(valor));
              return guardarMutacion.mutateAsync({ porcentaje_poblacion_acceso_internet: valor });
            }}
            onGuardarBandera={(valor) => {
              setPorcentajePoblacionAccesoInternetNoSeTieneDato(valor);
              return guardarMutacion.mutateAsync({ porcentaje_poblacion_acceso_internet_no_se_tiene_dato: valor });
            }}
          />
          <CampoSelect
            id="accesibilidad_sistemas_discapacidad"
            etiqueta="¿Los sistemas o portales digitales del gobierno cumplen, en general, con estándares de accesibilidad para personas con discapacidad?"
            opciones={SI_NO_PARCIALMENTE_OPCIONES}
            valor={accesibilidadSistemasDiscapacidad}
            onGuardar={(valor) => {
              setAccesibilidadSistemasDiscapacidad(valor);
              return guardarMutacion.mutateAsync({ accesibilidad_sistemas_discapacidad: valor });
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
            onGuardar={(valor) => {
              setCatalogoTramitesPropioExiste(valor);
              return guardarMutacion.mutateAsync({ catalogo_tramites_propio_existe: valor });
            }}
          />
        </CardContent>
      </Card>
    </div>
  );
}

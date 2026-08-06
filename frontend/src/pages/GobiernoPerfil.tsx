import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  type Conectividad,
  type ContextoInstitucionalPayload,
  type ContextoInstitucionalResponse,
  guardarContextoInstitucional,
  obtenerContextoInstitucional,
} from "@/lib/gobiernoContextoApi";
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
  { valor: "sin_conexion", etiqueta: "Sin conexión" },
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

function CampoNumerico({
  etiqueta,
  ayuda,
  valorInicial,
  guardando,
  error,
  onGuardar,
}: {
  etiqueta: string;
  ayuda?: string;
  valorInicial: string;
  guardando: boolean;
  error: boolean;
  onGuardar: (valor: number) => void;
}) {
  const [valor, setValor] = useState(valorInicial);

  useEffect(() => {
    setValor(valorInicial);
  }, [valorInicial]);

  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium">{etiqueta}</label>
      <Input
        type="number"
        min={0}
        inputMode="numeric"
        value={valor}
        onChange={(e) => setValor(e.target.value)}
        onBlur={() => {
          const numero = Number(valor);
          if (valor.trim() !== "" && Number.isFinite(numero) && numero >= 0 && valor !== valorInicial) {
            onGuardar(numero);
          }
        }}
        className="sm:w-64"
      />
      {ayuda && <p className="text-xs text-atenuado">{ayuda}</p>}
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

export function GobiernoPerfil() {
  const pais = obtenerPais();
  const queryClient = useQueryClient();
  const inicializadoRef = useRef(false);

  const [poblacionTotal, setPoblacionTotal] = useState("");
  const [personalTotalGobierno, setPersonalTotalGobierno] = useState("");
  const [presupuestoTicAnual, setPresupuestoTicAnual] = useState("");
  const [areaTicExiste, setAreaTicExiste] = useState<boolean | null>(null);
  const [conectividad, setConectividad] = useState<Conectividad | null>(null);
  const [normativaLocalEmitida, setNormativaLocalEmitida] = useState<boolean | null>(null);
  const [autoridadGobernanzaDigital, setAutoridadGobernanzaDigital] = useState<boolean | null>(null);

  const [campoGuardando, setCampoGuardando] = useState<string | null>(null);
  const [campoConError, setCampoConError] = useState<string | null>(null);

  const contextoQuery = useQuery({
    queryKey: ["gobierno-contexto"],
    queryFn: obtenerContextoInstitucional,
  });

  useEffect(() => {
    const datos = contextoQuery.data;
    if (!datos || inicializadoRef.current) return;
    inicializadoRef.current = true;

    if (datos.poblacion_total !== null) setPoblacionTotal(String(datos.poblacion_total));
    if (datos.personal_total_gobierno !== null) setPersonalTotalGobierno(String(datos.personal_total_gobierno));
    if (datos.presupuesto_tic_anual !== null) setPresupuestoTicAnual(String(datos.presupuesto_tic_anual));
    setAreaTicExiste(datos.area_tic_existe);
    setConectividad(datos.conectividad);
    setNormativaLocalEmitida(datos.normativa_local_emitida);
    setAutoridadGobernanzaDigital(datos.autoridad_gobernanza_digital);
  }, [contextoQuery.data]);

  const guardarMutacion = useMutation({
    mutationFn: (payload: ContextoInstitucionalPayload) => guardarContextoInstitucional(payload),
    onSuccess: (respuesta: ContextoInstitucionalResponse) => {
      queryClient.setQueryData(["gobierno-contexto"], respuesta);
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
        </CardContent>
      </Card>
    </div>
  );
}

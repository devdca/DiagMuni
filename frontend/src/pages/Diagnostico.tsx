import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Textarea } from "@/components/ui/textarea";
import { clasificarConsistenciaBooleana, clasificarMecanismoIdentidad } from "@/lib/asistenteCapturaApi";
import {
  enviarDiagnostico,
  guardarDiagnostico,
  obtenerDiagnostico,
  type RespuestasDiagnostico,
} from "@/lib/diagnosticoApi";
import { cn } from "@/lib/utils";
import { planListo } from "@/lib/planApi";
import { obtenerPais } from "@/lib/session";
import { obtenerTramite } from "@/lib/tramitesApi";

// Cuestionario de captura (F1 producto), docs/ux-brief.md sección "3. Cuestionario
// de captura (F1)": un Card por cada una de las 6 variables reales del catálogo
// (docs/backend-schema.md), sin ramificación condicional real -- no existe hoy
// ninguna dependencia documentada entre estas 6 variables (docs/ux-brief.md línea
// 68 es solo un ejemplo ilustrativo, no una regla implementada).

type IdBooleano =
  | "documentos_digitalizados"
  | "motor_pagos"
  | "firma_electronica_habilitada"
  | "interoperabilidad"
  | "proteccion_datos_incompleta";

interface PreguntaBooleana {
  id: IdBooleano;
  pregunta: string;
  ayuda: string;
}

const PREGUNTAS_BOOLEANAS: PreguntaBooleana[] = [
  {
    id: "documentos_digitalizados",
    pregunta: "¿Los documentos que se necesitan para este trámite ya están digitalizados?",
    ayuda:
      "Responda \"Sí\" solo si el expediente completo del trámite ya existe en formato digital, no solo escaneado como respaldo. Si el expediente sigue siendo en papel, es el primer paso a resolver antes de cualquier otro avance.",
  },
  {
    id: "motor_pagos",
    pregunta: "¿El ciudadano puede pagar este trámite en línea?",
    ayuda:
      "Se refiere a una forma de pago electrónico real para este trámite (tarjeta, transferencia, etc.). Si solo se acepta depósito bancario sin conciliación automática, aclárelo abajo.",
  },
  {
    id: "firma_electronica_habilitada",
    pregunta: "¿Este trámite acepta firma electrónica en vez de firma en papel?",
    ayuda:
      "Aplica si el ciudadano o el funcionario pueden firmar los documentos del trámite de forma electrónica, con validez legal.",
  },
  {
    id: "interoperabilidad",
    pregunta: "¿Este trámite comparte información automáticamente con otros registros de gobierno?",
    ayuda:
      "Por ejemplo, si al capturar un dato el sistema lo verifica automáticamente contra otro registro, sin pedirle al ciudadano el mismo documento otra vez.",
  },
  {
    id: "proteccion_datos_incompleta",
    pregunta: "¿Falta completar alguna medida de protección de datos personales para este trámite?",
    ayuda:
      "Por ejemplo, si todavía no se publica un aviso de privacidad, o si los datos capturados no están debidamente resguardados.",
  },
];

const OPCION_OTRO = "otro";

const ETIQUETA_MECANISMO: Record<string, string> = {
  llave_mx: "Llave MX",
  id_uruguay: "ID Uruguay",
  propio: "Un mecanismo propio de este gobierno",
  ninguno: "Ninguno",
};

function opcionesMecanismo(pais: string | null): { valor: string; etiqueta: string }[] {
  const opciones: { valor: string; etiqueta: string }[] = [];
  if (pais === "mx") opciones.push({ valor: "llave_mx", etiqueta: ETIQUETA_MECANISMO.llave_mx });
  if (pais === "uy") opciones.push({ valor: "id_uruguay", etiqueta: ETIQUETA_MECANISMO.id_uruguay });
  opciones.push({ valor: "propio", etiqueta: ETIQUETA_MECANISMO.propio });
  opciones.push({ valor: "ninguno", etiqueta: ETIQUETA_MECANISMO.ninguno });
  opciones.push({ valor: OPCION_OTRO, etiqueta: "Otro, especifique" });
  return opciones;
}

type ValoresBooleanos = Record<IdBooleano, boolean | null>;
type Aclaraciones = Record<string, string>;
type SugerenciasBooleanas = Record<IdBooleano, string | null>;

const VALORES_INICIALES: ValoresBooleanos = {
  documentos_digitalizados: null,
  motor_pagos: null,
  firma_electronica_habilitada: null,
  interoperabilidad: null,
  proteccion_datos_incompleta: null,
};

const SUGERENCIAS_INICIALES: SugerenciasBooleanas = {
  documentos_digitalizados: null,
  motor_pagos: null,
  firma_electronica_habilitada: null,
  interoperabilidad: null,
  proteccion_datos_incompleta: null,
};

// --- Card de aclaración opcional (compartida por las 6 preguntas) ------------------

function CampoAclaracion({
  id,
  abiertoPorDefecto,
  obligatorio,
  valor,
  onChange,
  onSalir,
  clasificando,
}: {
  id: string;
  abiertoPorDefecto: boolean;
  obligatorio: boolean;
  valor: string;
  onChange: (texto: string) => void;
  onSalir: () => void;
  clasificando: boolean;
}) {
  const [abierto, setAbierto] = useState(abiertoPorDefecto);

  if (!abierto && !obligatorio) {
    return (
      <button
        type="button"
        onClick={() => setAbierto(true)}
        className="text-left text-xs text-muted-foreground underline underline-offset-2"
      >
        ¿Su situación no encaja en esta opción? Explique aquí
      </button>
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-xs font-medium text-muted-foreground">
        {obligatorio ? "Especifique (obligatorio)" : "Aclaración (opcional)"}
      </label>
      <Textarea
        id={id}
        value={valor}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onSalir}
        required={obligatorio}
        rows={2}
      />
      {clasificando && <p className="text-xs text-atenuado">Revisando su explicación…</p>}
    </div>
  );
}

// --- Card de pregunta booleana ------------------------------------------------------

function CardBooleana({
  definicion,
  valor,
  aclaracion,
  sugerencia,
  clasificando,
  onCambiarValor,
  onCambiarAclaracion,
  onSalirAclaracion,
  onConfirmarSugerencia,
  onDescartarSugerencia,
}: {
  definicion: PreguntaBooleana;
  valor: boolean | null;
  aclaracion: string;
  sugerencia: string | null;
  clasificando: boolean;
  onCambiarValor: (valor: boolean) => void;
  onCambiarAclaracion: (texto: string) => void;
  onSalirAclaracion: () => void;
  onConfirmarSugerencia: () => void;
  onDescartarSugerencia: () => void;
}) {
  const sugiereSi = sugerencia === "posible_contradiccion_hacia_si";
  const sugiereNo = sugerencia === "posible_contradiccion_hacia_no";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-medium">{definicion.pregunta}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <RadioGroup
          value={valor === null ? undefined : valor ? "si" : "no"}
          onValueChange={(v) => onCambiarValor(v === "si")}
          className="grid grid-cols-2 gap-3 sm:w-64"
        >
          {(["si", "no"] as const).map((opcion) => (
            <label
              key={opcion}
              htmlFor={`${definicion.id}-${opcion}`}
              className={cn(
                "flex min-h-11 cursor-pointer items-center gap-3 rounded-md border px-3 py-2",
                (valor === true && opcion === "si") || (valor === false && opcion === "no")
                  ? "border-primary"
                  : "border-border",
              )}
            >
              <RadioGroupItem value={opcion} id={`${definicion.id}-${opcion}`} />
              <span className="text-sm">{opcion === "si" ? "Sí" : "No"}</span>
            </label>
          ))}
        </RadioGroup>

        <p className="text-xs text-atenuado">{definicion.ayuda}</p>

        <CampoAclaracion
          id={`aclaracion-${definicion.id}`}
          abiertoPorDefecto={false}
          obligatorio={false}
          valor={aclaracion}
          onChange={onCambiarAclaracion}
          onSalir={onSalirAclaracion}
          clasificando={clasificando}
        />

        {(sugiereSi || sugiereNo) && (
          <div className="rounded-md border border-border bg-secondary px-3 py-2 text-sm">
            <p>
              Según su aclaración, esto podría en realidad ser <strong>{sugiereSi ? "Sí" : "No"}</strong>. ¿Es
              correcto?
            </p>
            <div className="mt-2 flex gap-2">
              <Button type="button" size="sm" onClick={onConfirmarSugerencia}>
                Confirmar
              </Button>
              <Button type="button" size="sm" variant="outline" onClick={onDescartarSugerencia}>
                Elegir manualmente
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// --- Card de mecanismo_identidad -----------------------------------------------------

function CardMecanismoIdentidad({
  pais,
  seleccion,
  aclaracion,
  sugerencia,
  clasificando,
  onCambiarSeleccion,
  onCambiarAclaracion,
  onSalirAclaracion,
  onConfirmarSugerencia,
  onDescartarSugerencia,
}: {
  pais: string | null;
  seleccion: string | null;
  aclaracion: string;
  sugerencia: string | null;
  clasificando: boolean;
  onCambiarSeleccion: (valor: string) => void;
  onCambiarAclaracion: (texto: string) => void;
  onSalirAclaracion: () => void;
  onConfirmarSugerencia: () => void;
  onDescartarSugerencia: () => void;
}) {
  const opciones = opcionesMecanismo(pais);
  const esOtro = seleccion === OPCION_OTRO;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-medium">
          ¿Con qué mecanismo se identifica el ciudadano para este trámite?
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <RadioGroup
          value={seleccion ?? undefined}
          onValueChange={onCambiarSeleccion}
          className="grid gap-3 sm:max-w-md"
        >
          {opciones.map((opcion) => (
            <label
              key={opcion.valor}
              htmlFor={`mecanismo-${opcion.valor}`}
              className={cn(
                "flex min-h-11 cursor-pointer items-center gap-3 rounded-md border px-3 py-2",
                seleccion === opcion.valor ? "border-primary" : "border-border",
              )}
            >
              <RadioGroupItem value={opcion.valor} id={`mecanismo-${opcion.valor}`} />
              <span className="text-sm">{opcion.etiqueta}</span>
            </label>
          ))}
        </RadioGroup>

        <p className="text-xs text-atenuado">
          Por ejemplo, una credencial digital nacional, un usuario propio de este gobierno, o si no existe ningún
          mecanismo de identificación en línea.
        </p>

        <CampoAclaracion
          id="aclaracion-mecanismo_identidad"
          abiertoPorDefecto={esOtro}
          obligatorio={esOtro}
          valor={aclaracion}
          onChange={onCambiarAclaracion}
          onSalir={onSalirAclaracion}
          clasificando={clasificando}
        />

        {esOtro && sugerencia && (
          <div className="rounded-md border border-border bg-secondary px-3 py-2 text-sm">
            <p>
              Según su descripción, esto parece corresponder a: <strong>{ETIQUETA_MECANISMO[sugerencia]}</strong>. ¿Es
              correcto?
            </p>
            <div className="mt-2 flex gap-2">
              <Button type="button" size="sm" onClick={onConfirmarSugerencia}>
                Confirmar
              </Button>
              <Button type="button" size="sm" variant="outline" onClick={onDescartarSugerencia}>
                Elegir manualmente
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// --- Pantalla principal --------------------------------------------------------------

export function Diagnostico() {
  const { tramiteId } = useParams<{ tramiteId: string }>();
  const navigate = useNavigate();
  const pais = obtenerPais();

  const [valores, setValores] = useState<ValoresBooleanos>(VALORES_INICIALES);
  const [aclaraciones, setAclaraciones] = useState<Aclaraciones>({});
  const [sugerencias, setSugerencias] = useState<SugerenciasBooleanas>(SUGERENCIAS_INICIALES);
  const [clasificandoBooleana, setClasificandoBooleana] = useState<Record<IdBooleano, boolean>>({
    documentos_digitalizados: false,
    motor_pagos: false,
    firma_electronica_habilitada: false,
    interoperabilidad: false,
    proteccion_datos_incompleta: false,
  });

  const [mecanismoSeleccion, setMecanismoSeleccion] = useState<string | null>(null);
  const [mecanismoAclaracion, setMecanismoAclaracion] = useState("");
  const [mecanismoSugerencia, setMecanismoSugerencia] = useState<string | null>(null);
  const [clasificandoMecanismo, setClasificandoMecanismo] = useState(false);

  const [esperandoPlan, setEsperandoPlan] = useState(false);

  const inicializadoRef = useRef(false);

  const diagnosticoQuery = useQuery({
    queryKey: ["diagnostico", tramiteId],
    queryFn: () => obtenerDiagnostico(tramiteId!),
    enabled: !!tramiteId,
  });

  // Fuente de verdad del estado real del trámite -- distingue un job de plan
  // efectivamente en curso (estado "generando_plan") de un diagnóstico que
  // simplemente fue enviado en algún momento del pasado (docs/app-flow.md:
  // reabrir y modificar respuestas debe regresar el trámite a "en_progreso").
  const tramiteQuery = useQuery({
    queryKey: ["tramite", tramiteId],
    queryFn: () => obtenerTramite(tramiteId!),
    enabled: !!tramiteId,
  });

  useEffect(() => {
    const datos = diagnosticoQuery.data;
    if (!datos || inicializadoRef.current) return;
    inicializadoRef.current = true;

    const respuestas = datos.respuestas ?? {};
    setValores((prev) => {
      const siguiente = { ...prev };
      for (const pregunta of PREGUNTAS_BOOLEANAS) {
        const valor = respuestas[pregunta.id];
        if (typeof valor === "boolean") siguiente[pregunta.id] = valor;
      }
      return siguiente;
    });
    if (typeof respuestas.mecanismo_identidad === "string") {
      setMecanismoSeleccion(respuestas.mecanismo_identidad);
    }
    if (respuestas.aclaraciones && typeof respuestas.aclaraciones === "object") {
      const { mecanismo_identidad: aclaracionMecanismoCargada, ...aclaracionesBooleanas } = respuestas.aclaraciones;
      if (typeof aclaracionMecanismoCargada === "string") {
        setMecanismoAclaracion(aclaracionMecanismoCargada);
      }
      setAclaraciones((prev) => ({ ...prev, ...aclaracionesBooleanas }));
    }
  }, [diagnosticoQuery.data]);

  // Solo un job de plan efectivamente en curso al momento de cargar la
  // pantalla debe mostrar la espera; "completado_en" por sí solo no lo indica
  // porque nunca se limpia una vez fijado. Efecto independiente de la precarga
  // de respuestas para no atar su temporización a la de esta consulta.
  useEffect(() => {
    if (tramiteQuery.data?.estado === "generando_plan") {
      setEsperandoPlan(true);
    }
  }, [tramiteQuery.data]);

  // Polling de "generando plan" (docs/app-flow.md línea 55): el índice F2 ya se
  // calculó de forma síncrona al enviar; el job de plan puede tardar. Nunca
  // bloquea el resto de la navegación -- el funcionario puede volver al panel.
  useEffect(() => {
    if (!esperandoPlan || !tramiteId) return;
    let cancelado = false;

    async function verificar() {
      try {
        const listo = await planListo(tramiteId!);
        if (listo && !cancelado) {
          navigate(`/tramites/${tramiteId}/plan`);
        }
      } catch {
        // Fallo de red transitorio -- se reintenta en el siguiente tick, nunca
        // muestra un error de por sí (el funcionario puede irse y volver).
      }
    }

    verificar();
    const intervalo = setInterval(verificar, 3000);
    return () => {
      cancelado = true;
      clearInterval(intervalo);
    };
  }, [esperandoPlan, tramiteId, navigate]);

  function construirRespuestas(): RespuestasDiagnostico {
    const respuestas: RespuestasDiagnostico = {};
    for (const pregunta of PREGUNTAS_BOOLEANAS) {
      const valor = valores[pregunta.id];
      if (valor !== null) respuestas[pregunta.id] = valor;
    }
    if (mecanismoSeleccion && mecanismoSeleccion !== OPCION_OTRO) {
      respuestas.mecanismo_identidad = mecanismoSeleccion;
    }
    const aclaracionesNoVacias = Object.fromEntries(
      Object.entries({ ...aclaraciones, mecanismo_identidad: mecanismoAclaracion }).filter(
        ([, texto]) => texto.trim().length > 0,
      ),
    );
    if (Object.keys(aclaracionesNoVacias).length > 0) {
      respuestas.aclaraciones = aclaracionesNoVacias;
    }
    return respuestas;
  }

  const guardarMutacion = useMutation({
    mutationFn: () => guardarDiagnostico(tramiteId!, construirRespuestas()),
    onSuccess: () => navigate("/"),
  });

  const enviarMutacion = useMutation({
    mutationFn: () => enviarDiagnostico(tramiteId!, construirRespuestas()),
    onSuccess: () => setEsperandoPlan(true),
  });

  async function alSalirAclaracionBooleana(id: IdBooleano) {
    const texto = aclaraciones[id] ?? "";
    const valorActual = valores[id];
    if (!texto.trim() || valorActual === null) return;

    setClasificandoBooleana((prev) => ({ ...prev, [id]: true }));
    try {
      const { categoria } = await clasificarConsistenciaBooleana(texto, valorActual);
      const esSugerenciaDeContradiccion =
        categoria === "posible_contradiccion_hacia_si" || categoria === "posible_contradiccion_hacia_no";
      setSugerencias((prev) => ({ ...prev, [id]: esSugerenciaDeContradiccion ? categoria : null }));
    } catch {
      // Fail-safe: sin sugerencia visible, la aclaración ya quedó guardada como
      // texto de apoyo -- mismo comportamiento que si la clasificación no existiera.
      setSugerencias((prev) => ({ ...prev, [id]: null }));
    } finally {
      setClasificandoBooleana((prev) => ({ ...prev, [id]: false }));
    }
  }

  async function alSalirAclaracionMecanismo() {
    if (mecanismoSeleccion !== OPCION_OTRO || !mecanismoAclaracion.trim()) return;

    setClasificandoMecanismo(true);
    try {
      const { categoria } = await clasificarMecanismoIdentidad(mecanismoAclaracion);
      setMecanismoSugerencia(categoria in ETIQUETA_MECANISMO ? categoria : null);
    } catch {
      setMecanismoSugerencia(null);
    } finally {
      setClasificandoMecanismo(false);
    }
  }

  const todasBooleanasRespondidas = PREGUNTAS_BOOLEANAS.every((p) => valores[p.id] !== null);
  const mecanismoResuelto = mecanismoSeleccion !== null && mecanismoSeleccion !== OPCION_OTRO;
  const listoParaEnviar = todasBooleanasRespondidas && mecanismoResuelto;

  const totalPreguntas = PREGUNTAS_BOOLEANAS.length + 1;
  const respondidas = PREGUNTAS_BOOLEANAS.filter((p) => valores[p.id] !== null).length + (mecanismoResuelto ? 1 : 0);
  const avance = Math.round((respondidas / totalPreguntas) * 100);

  if (!tramiteId) return null;

  if (diagnosticoQuery.isLoading) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-sm text-atenuado">Cargando...</p>
      </div>
    );
  }

  if (esperandoPlan) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4 p-6">
        <Card>
          <CardHeader>
            <CardTitle>Generando plan de modernización…</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <p className="text-sm text-muted-foreground">
              Ya guardamos su diagnóstico. Estamos preparando el plan de modernización; esto puede tardar un
              momento.
            </p>
            <Button variant="outline" onClick={() => navigate("/")}>
              Volver al panel resumen
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">Cuestionario de diagnóstico</h2>
        <Progress value={avance} />
        <p className="text-xs text-atenuado">
          {respondidas} de {totalPreguntas} preguntas respondidas
        </p>
      </div>

      {PREGUNTAS_BOOLEANAS.map((definicion) => (
        <CardBooleana
          key={definicion.id}
          definicion={definicion}
          valor={valores[definicion.id]}
          aclaracion={aclaraciones[definicion.id] ?? ""}
          sugerencia={sugerencias[definicion.id]}
          clasificando={clasificandoBooleana[definicion.id]}
          onCambiarValor={(valor) => setValores((prev) => ({ ...prev, [definicion.id]: valor }))}
          onCambiarAclaracion={(texto) => setAclaraciones((prev) => ({ ...prev, [definicion.id]: texto }))}
          onSalirAclaracion={() => alSalirAclaracionBooleana(definicion.id)}
          onConfirmarSugerencia={() => {
            const sugerencia = sugerencias[definicion.id];
            if (sugerencia) {
              setValores((prev) => ({ ...prev, [definicion.id]: sugerencia === "posible_contradiccion_hacia_si" }));
            }
            setSugerencias((prev) => ({ ...prev, [definicion.id]: null }));
          }}
          onDescartarSugerencia={() => setSugerencias((prev) => ({ ...prev, [definicion.id]: null }))}
        />
      ))}

      <CardMecanismoIdentidad
        pais={pais}
        seleccion={mecanismoSeleccion}
        aclaracion={mecanismoAclaracion}
        sugerencia={mecanismoSugerencia}
        clasificando={clasificandoMecanismo}
        onCambiarSeleccion={(valor) => {
          setMecanismoSeleccion(valor);
          setMecanismoSugerencia(null);
        }}
        onCambiarAclaracion={setMecanismoAclaracion}
        onSalirAclaracion={alSalirAclaracionMecanismo}
        onConfirmarSugerencia={() => {
          if (mecanismoSugerencia) setMecanismoSeleccion(mecanismoSugerencia);
          setMecanismoSugerencia(null);
        }}
        onDescartarSugerencia={() => setMecanismoSugerencia(null)}
      />

      {(guardarMutacion.isError || enviarMutacion.isError) && (
        <p role="alert" className="text-sm text-destructive">
          No se pudo completar la operación. Intenta de nuevo.
        </p>
      )}

      <div className="flex flex-wrap gap-3">
        <Button variant="outline" onClick={() => guardarMutacion.mutate()} disabled={guardarMutacion.isPending}>
          {guardarMutacion.isPending ? "Guardando..." : "Guardar y continuar después"}
        </Button>
        <Button
          onClick={() => enviarMutacion.mutate()}
          disabled={!listoParaEnviar || enviarMutacion.isPending}
          title={!listoParaEnviar ? "Responda todas las preguntas antes de enviar" : undefined}
        >
          {enviarMutacion.isPending ? "Enviando..." : "Enviar diagnóstico"}
        </Button>
      </div>
    </div>
  );
}

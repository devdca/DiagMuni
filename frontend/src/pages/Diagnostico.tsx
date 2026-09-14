import { useEffect, useMemo, useRef, useState } from "react";
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
  simularDiagnostico,
  type RespuestasDiagnostico,
  type SimulacionResponse,
} from "@/lib/diagnosticoApi";
import { ApiError } from "@/lib/httpClient";
import { obtenerNivelMadurez } from "@/lib/madurez";
import { cn } from "@/lib/utils";
import { planListo } from "@/lib/planApi";
import { obtenerPais } from "@/lib/session";
import { obtenerTiposTramite, obtenerTramite } from "@/lib/tramitesApi";

// Cuestionario de captura (F1 producto), docs/ux-brief.md sección "3. Cuestionario
// de captura (F1)": un Card por cada una de las 6 variables reales del catálogo
// (docs/backend-schema.md) -- `preguntasEfectivas` excluye las que no aplican al
// tipo de trámite (app/engine/tipos_tramite.yaml), `mecanismo_identidad` siempre
// se muestra.

type IdBooleano =
  | "documentos_digitalizados"
  | "motor_pagos"
  | "firma_electronica_habilitada"
  | "interoperabilidad"
  | "proteccion_datos_incompleta"
  | "tramite_completo_en_linea"
  | "registrado_portal_ciudadano_unico"
  | "notificaciones_automaticas"
  | "disponible_movil"
  | "plazo_respuesta_publicado"
  | "silencio_administrativo_definido"
  | "mecanismo_quejas_digital"
  | "fundamento_juridico_vigente"
  | "costo_publicado_en_linea"
  | "revisado_ultimos_12_meses"
  | "personal_capacitado_tramite_digital"
  | "medicion_tiempo_satisfaccion"
  | "version_accesible"
  | "atencion_lengua_indigena"
  | "requisitos_publicados_claramente";

interface PreguntaBooleana {
  id: IdBooleano;
  pregunta: string;
  ayuda: string;
  seccion: string;
}

const PREGUNTAS_BOOLEANAS: PreguntaBooleana[] = [
  {
    id: "documentos_digitalizados",
    pregunta: "¿Los documentos que se necesitan para este trámite ya están digitalizados?",
    ayuda:
      "Responda \"Sí\" solo si el expediente completo del trámite ya existe en formato digital, no solo escaneado como respaldo. Si el expediente sigue siendo en papel, es el primer paso a resolver antes de cualquier otro avance.",
    seccion: "Digitalización",
  },
  {
    id: "motor_pagos",
    pregunta: "¿El ciudadano puede pagar este trámite en línea?",
    ayuda:
      "Se refiere a una forma de pago electrónico real para este trámite (tarjeta, transferencia, etc.). Si solo se acepta depósito bancario sin conciliación automática, aclárelo abajo.",
    seccion: "Digitalización",
  },
  {
    id: "firma_electronica_habilitada",
    pregunta: "¿Este trámite acepta firma electrónica en vez de firma en papel?",
    ayuda:
      "Aplica si el ciudadano o el funcionario pueden firmar los documentos del trámite de forma electrónica, con validez legal.",
    seccion: "Digitalización",
  },
  {
    id: "interoperabilidad",
    pregunta: "¿Este trámite comparte información automáticamente con otros registros de gobierno?",
    ayuda:
      "Por ejemplo, si al capturar un dato el sistema lo verifica automáticamente contra otro registro, sin pedirle al ciudadano el mismo documento otra vez.",
    seccion: "Digitalización",
  },
  {
    id: "tramite_completo_en_linea",
    pregunta:
      "¿Este trámite se puede iniciar y concluir completamente en línea, incluyendo la entrega del resultado?",
    ayuda:
      "Distinto de que solo el expediente esté digitalizado: aquí importa que el ciudadano no tenga que acudir en persona en ningún paso, ni siquiera para recoger el resultado final.",
    seccion: "Digitalización",
  },
  {
    id: "registrado_portal_ciudadano_unico",
    pregunta: "¿Este trámite está registrado en el Portal Ciudadano Único de Trámites y Servicios?",
    ayuda:
      "Es el punto de consulta centralizado donde el ciudadano puede encontrar cualquier trámite de gobierno, sin importar el orden de gobierno que lo ofrezca.",
    seccion: "Digitalización",
  },
  {
    id: "notificaciones_automaticas",
    pregunta: "¿El ciudadano recibe notificaciones automáticas sobre el avance de este trámite?",
    ayuda:
      "Por ejemplo, un aviso por correo, SMS o app cuando el trámite cambia de estatus, sin que el ciudadano tenga que llamar o acudir a preguntar.",
    seccion: "Digitalización",
  },
  {
    id: "disponible_movil",
    pregunta: "¿Este trámite se puede iniciar y completar desde un dispositivo móvil?",
    ayuda: "No solo que la página se vea bien en el celular, sino que el flujo completo se pueda hacer desde ahí.",
    seccion: "Digitalización",
  },
  {
    id: "plazo_respuesta_publicado",
    pregunta: "¿Está definido y publicado el plazo máximo de respuesta de este trámite?",
    ayuda:
      "Si no hay un plazo específico en la ley que lo rige, aplica el plazo supletorio de 4 meses de la Ley Federal de Procedimiento Administrativo.",
    seccion: "Cumplimiento y transparencia",
  },
  {
    id: "silencio_administrativo_definido",
    pregunta:
      "¿Está definido y publicado el sentido del silencio administrativo (positivo o negativo) si el gobierno no responde a tiempo?",
    ayuda: "Determina qué debe esperar el ciudadano si el plazo de respuesta vence sin que el gobierno se pronuncie.",
    seccion: "Cumplimiento y transparencia",
  },
  {
    id: "mecanismo_quejas_digital",
    pregunta: "¿Existe un mecanismo digital de quejas o incidencias específico para este trámite?",
    ayuda:
      "Un canal donde el ciudadano pueda reportar un problema con este trámite en particular y darle seguimiento con un folio.",
    seccion: "Cumplimiento y transparencia",
  },
  {
    id: "fundamento_juridico_vigente",
    pregunta: "¿Se identificó y confirmó la vigencia del fundamento jurídico que rige este trámite?",
    ayuda: "Un trámite sin fundamento jurídico claro, o con uno derogado, puede ser impugnable.",
    seccion: "Cumplimiento y transparencia",
  },
  {
    id: "costo_publicado_en_linea",
    pregunta: "¿El costo de este trámite (si aplica) está publicado de forma clara y accesible en línea?",
    ayuda: "El ciudadano debe poder saber cuánto le va a costar sin tener que acudir a preguntar.",
    seccion: "Cumplimiento y transparencia",
  },
  {
    id: "requisitos_publicados_claramente",
    pregunta: "¿Los requisitos para iniciar este trámite están publicados de forma clara y completa en línea?",
    ayuda:
      "Distinto de que el expediente ya esté digitalizado: aquí importa que el ciudadano pueda saber qué necesita antes de empezar, sin tener que acudir a preguntar.",
    seccion: "Cumplimiento y transparencia",
  },
  {
    id: "revisado_ultimos_12_meses",
    pregunta: "¿Este trámite fue revisado o simplificado en los últimos 12 meses?",
    ayuda:
      "Por ejemplo, eliminando requisitos innecesarios. La Agenda de Simplificación y Digitalización exige revisión y publicación de avances cada semestre.",
    seccion: "Cumplimiento y transparencia",
  },
  {
    id: "proteccion_datos_incompleta",
    pregunta: "¿Falta completar alguna medida de protección de datos personales para este trámite?",
    ayuda:
      "Por ejemplo, si todavía no se publica un aviso de privacidad, o si los datos capturados no están debidamente resguardados.",
    seccion: "Cumplimiento y transparencia",
  },
  {
    id: "version_accesible",
    pregunta: "¿La versión digital de este trámite es accesible para personas con discapacidad?",
    ayuda: "Por ejemplo, compatible con lector de pantalla, buen contraste y navegación por teclado.",
    seccion: "Accesibilidad e inclusión",
  },
  {
    id: "atencion_lengua_indigena",
    pregunta:
      "¿Se ofrece atención en alguna lengua indígena o mediante intérprete para este trámite, cuando aplica en la región?",
    ayuda: "Las lenguas indígenas son válidas para cualquier trámite de carácter público en México.",
    seccion: "Accesibilidad e inclusión",
  },
  {
    id: "personal_capacitado_tramite_digital",
    pregunta: "¿El personal que opera este trámite está capacitado en su versión digital?",
    ayuda: "Ningún componente digital de este trámite rinde si el personal que lo opera no sabe usarlo.",
    seccion: "Capacidad y desempeño",
  },
  {
    id: "medicion_tiempo_satisfaccion",
    pregunta: "¿Se mide el tiempo real de resolución y/o la satisfacción ciudadana de este trámite?",
    ayuda: "Sin medición no hay forma de saber si el trámite realmente mejoró tras aplicar este plan.",
    seccion: "Capacidad y desempeño",
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

const VALORES_INICIALES: ValoresBooleanos = Object.fromEntries(
  PREGUNTAS_BOOLEANAS.map((p) => [p.id, null]),
) as ValoresBooleanos;

const SUGERENCIAS_INICIALES: SugerenciasBooleanas = Object.fromEntries(
  PREGUNTAS_BOOLEANAS.map((p) => [p.id, null]),
) as SugerenciasBooleanas;

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

// --- Card de una variable adicional (propia del tipo de trámite) --------------------
//
// Más simple que CardBooleana a propósito: sin aclaración ni sugerencia asistida por
// IA -- son preguntas nuevas, propias de app/engine/tipos_tramite.yaml, no del
// catálogo de 6 variables que ya tiene ese flujo.

function CardVariableAdicional({
  pregunta,
  ayuda,
  valor,
  onCambiarValor,
}: {
  pregunta: string;
  ayuda: string;
  valor: boolean | null;
  onCambiarValor: (valor: boolean) => void;
}) {
  const id = `adicional-${pregunta}`;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-medium">{pregunta}</CardTitle>
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
        <p className="text-xs text-atenuado">{ayuda}</p>
      </CardContent>
    </Card>
  );
}

// --- Contexto adicional (opcional, no genera brecha) --------------------------------
//
// volumen_demanda_anual y tramite_concurrente/tramite_concurrente_detalle no
// afectan el índice de madurez ni el catálogo de brechas -- solo alimentan
// app/ia/estimacion_recursos.py para que la estimación de personal/presupuesto
// sea más puntual. Por eso son opcionales, no bloquean "Enviar diagnóstico".

const OPCIONES_VOLUMEN_DEMANDA: { valor: string; etiqueta: string }[] = [
  { valor: "menos_100", etiqueta: "Menos de 100 al año" },
  { valor: "100_1000", etiqueta: "Entre 100 y 1,000 al año" },
  { valor: "1000_10000", etiqueta: "Entre 1,000 y 10,000 al año" },
  { valor: "mas_10000", etiqueta: "Más de 10,000 al año" },
  { valor: "no_se_mide", etiqueta: "No se mide" },
];

function CardVolumenDemanda({ valor, onCambiar }: { valor: string | null; onCambiar: (valor: string) => void }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-medium">
          ¿Aproximadamente cuántas solicitudes de este trámite se reciben al año?
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <RadioGroup value={valor ?? undefined} onValueChange={onCambiar} className="grid gap-3 sm:max-w-md">
          {OPCIONES_VOLUMEN_DEMANDA.map((opcion) => (
            <label
              key={opcion.valor}
              htmlFor={`volumen-${opcion.valor}`}
              className={cn(
                "flex min-h-11 cursor-pointer items-center gap-3 rounded-md border px-3 py-2",
                valor === opcion.valor ? "border-primary" : "border-border",
              )}
            >
              <RadioGroupItem value={opcion.valor} id={`volumen-${opcion.valor}`} />
              <span className="text-sm">{opcion.etiqueta}</span>
            </label>
          ))}
        </RadioGroup>
        <p className="text-xs text-atenuado">
          Ayuda a priorizar la inversión -- un trámite con mucha demanda no debería recibir el mismo nivel de
          inversión que uno con muy poca. Opcional.
        </p>
      </CardContent>
    </Card>
  );
}

function CardTramiteConcurrente({
  valor,
  detalle,
  onCambiarValor,
  onCambiarDetalle,
}: {
  valor: boolean | null;
  detalle: string;
  onCambiarValor: (valor: boolean) => void;
  onCambiarDetalle: (texto: string) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-medium">
          ¿Este trámite requiere la intervención de otra dependencia o de otro orden de gobierno para poder
          concluirse?
        </CardTitle>
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
              htmlFor={`concurrente-${opcion}`}
              className={cn(
                "flex min-h-11 cursor-pointer items-center gap-3 rounded-md border px-3 py-2",
                (valor === true && opcion === "si") || (valor === false && opcion === "no")
                  ? "border-primary"
                  : "border-border",
              )}
            >
              <RadioGroupItem value={opcion} id={`concurrente-${opcion}`} />
              <span className="text-sm">{opcion === "si" ? "Sí" : "No"}</span>
            </label>
          ))}
        </RadioGroup>
        <p className="text-xs text-atenuado">
          Distinto de si comparte información automáticamente con otros registros: aquí importa si el trámite
          depende de que otra dependencia u orden de gobierno intervenga para poder concluirse. Opcional.
        </p>
        {valor === true && (
          <div className="flex flex-col gap-1.5">
            <label htmlFor="concurrente-detalle" className="text-xs font-medium text-muted-foreground">
              ¿Cuál dependencia u orden de gobierno?
            </label>
            <Textarea
              id="concurrente-detalle"
              value={detalle}
              onChange={(e) => onCambiarDetalle(e.target.value)}
              rows={2}
            />
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
  errorClasificacion,
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
  errorClasificacion: boolean;
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

        {esOtro && !sugerencia && !clasificando && errorClasificacion && (
          <p role="alert" className="rounded-md border border-destructive/50 bg-destructive/5 px-3 py-2 text-sm">
            No pudimos determinar automáticamente a qué opción corresponde su descripción. Seleccione una de las
            opciones de la lista de arriba para poder enviar el diagnóstico.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// --- Panel de proyección en vivo ("qué pasa si") -------------------------------------
//
// Corre el motor determinista sobre las respuestas actuales del formulario, sin
// guardar nada (backend/app/adaptadores/http/diagnosticos.py::simular_diagnostico)
// -- deja ver el impacto de una respuesta antes de "Guardar" o "Enviar".

function PanelProyeccion({ simulacion, cargando }: { simulacion: SimulacionResponse | null; cargando: boolean }) {
  if (simulacion === null) return null;

  const actual = simulacion.indice_actual;
  const proyectado = simulacion.indice_proyectado;
  const nivelProyectado = obtenerNivelMadurez(proyectado);
  const cambia = actual !== null && actual !== proyectado;

  return (
    <Card className="lg:sticky lg:top-24 lg:self-start">
      <CardHeader>
        <CardTitle className="text-base">Proyección en vivo</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex items-center gap-4">
          {actual !== null && (
            <>
              <div className="text-center">
                <div className="text-[0.65rem] tracking-wide text-atenuado uppercase">Actual</div>
                <div className="text-2xl font-semibold text-atenuado tabular-nums">{actual}</div>
              </div>
              <span aria-hidden className="text-atenuado">
                →
              </span>
            </>
          )}
          <div className="text-center">
            <div className="text-[0.65rem] tracking-wide text-atenuado uppercase">
              {actual !== null ? "Con estas respuestas" : "Si envías así"}
            </div>
            <div className="text-3xl font-semibold tabular-nums" style={{ color: nivelProyectado.varTexto }}>
              {proyectado}
            </div>
          </div>
        </div>
        <p className="text-sm" style={{ color: nivelProyectado.varTexto }}>
          {nivelProyectado.etiqueta}
        </p>
        {cambia && (
          <p className="text-xs text-atenuado">
            {proyectado > (actual ?? 0)
              ? "Estas respuestas suben el índice respecto al diagnóstico ya guardado."
              : "Estas respuestas bajan el índice respecto al diagnóstico ya guardado."}
          </p>
        )}
        <p className="border-t border-border pt-2 text-xs text-atenuado">
          {cargando
            ? "Calculando..."
            : "Cálculo instantáneo del motor determinista sobre tus respuestas actuales -- no se guarda nada hasta enviar."}
        </p>
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
  const [clasificandoBooleana, setClasificandoBooleana] = useState<Record<IdBooleano, boolean>>(
    Object.fromEntries(PREGUNTAS_BOOLEANAS.map((p) => [p.id, false])) as Record<IdBooleano, boolean>,
  );

  const [valoresAdicionales, setValoresAdicionales] = useState<Record<string, boolean | null>>({});

  const [volumenDemanda, setVolumenDemanda] = useState<string | null>(null);
  const [tramiteConcurrente, setTramiteConcurrente] = useState<boolean | null>(null);
  const [tramiteConcurrenteDetalle, setTramiteConcurrenteDetalle] = useState("");

  const [mecanismoSeleccion, setMecanismoSeleccion] = useState<string | null>(null);
  const [mecanismoAclaracion, setMecanismoAclaracion] = useState("");
  const [mecanismoSugerencia, setMecanismoSugerencia] = useState<string | null>(null);
  const [clasificandoMecanismo, setClasificandoMecanismo] = useState(false);
  const [mecanismoErrorClasificacion, setMecanismoErrorClasificacion] = useState(false);

  const [esperandoPlan, setEsperandoPlan] = useState(false);

  const [simulacion, setSimulacion] = useState<SimulacionResponse | null>(null);
  const [simulando, setSimulando] = useState(false);

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

  // Qué preguntas aplican según el tipo de trámite (backend/app/engine/
  // tipos_tramite.yaml) -- mientras no se sepa el tipo (catálogo o trámite sin
  // cargar todavía), no se excluye nada, se muestran las 6 de siempre.
  const tiposQuery = useQuery({ queryKey: ["tipos-tramite"], queryFn: obtenerTiposTramite });
  const tipoTramiteActual = tiposQuery.data?.find((t) => t.nombre === tramiteQuery.data?.tipo);
  const variablesExcluidas = new Set(tipoTramiteActual?.variables_excluidas ?? []);
  const preguntasEfectivas = PREGUNTAS_BOOLEANAS.filter((p) => !variablesExcluidas.has(p.id));
  // Agrupa por sección preservando el orden en que aparece cada una en
  // PREGUNTAS_BOOLEANAS -- solo para presentación, no afecta qué se envía.
  const seccionesOrdenadas = [...new Set(preguntasEfectivas.map((p) => p.seccion))];
  const preguntasPorSeccion = seccionesOrdenadas.map((seccion) => ({
    seccion,
    preguntas: preguntasEfectivas.filter((p) => p.seccion === seccion),
  }));
  // Preguntas propias del tipo de trámite, además de las 6 de siempre. useMemo
  // sobre los datos crudos (no sobre `tipoTramiteActual`, que es un objeto nuevo
  // en cada render) para que la referencia sea estable en deps de useEffect.
  const variablesAdicionales = useMemo(
    () => tiposQuery.data?.find((t) => t.nombre === tramiteQuery.data?.tipo)?.variables_adicionales ?? [],
    [tiposQuery.data, tramiteQuery.data?.tipo],
  );

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
    if (typeof respuestas.volumen_demanda_anual === "string") {
      setVolumenDemanda(respuestas.volumen_demanda_anual);
    }
    if (typeof respuestas.tramite_concurrente === "boolean") {
      setTramiteConcurrente(respuestas.tramite_concurrente);
    }
    if (typeof respuestas.tramite_concurrente_detalle === "string") {
      setTramiteConcurrenteDetalle(respuestas.tramite_concurrente_detalle);
    }
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
    for (const va of variablesAdicionales) {
      const valor = respuestas[va.variable];
      if (typeof valor === "boolean") {
        setValoresAdicionales((prev) => ({ ...prev, [va.variable]: valor }));
      }
    }
  }, [diagnosticoQuery.data, variablesAdicionales]);

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
          await navigate(`/tramites/${tramiteId}/plan`);
        }
      } catch {
        // Fallo de red transitorio -- se reintenta en el siguiente tick, nunca
        // muestra un error de por sí (el funcionario puede irse y volver).
      }
    }

    void verificar();
    const intervalo = setInterval(() => void verificar(), 3000);
    return () => {
      cancelado = true;
      clearInterval(intervalo);
    };
  }, [esperandoPlan, tramiteId, navigate]);

  // Simulador "qué pasa si" (proyección en vivo, panel lateral): debounced 500ms,
  // solo dispara sobre las 4 variables booleanas + mecanismo_identidad que
  // realmente alimentan el índice de madurez (backend/app/dominio/madurez.py) --
  // el resto del formulario (transparencia, contexto opcional) no cambia el
  // resultado, recalcular por esos cambios sería una llamada desperdiciada.
  useEffect(() => {
    if (!tramiteId || esperandoPlan) return;
    let cancelado = false;

    const id = setTimeout(() => {
      setSimulando(true);
      simularDiagnostico(tramiteId, construirRespuestas())
        .then((resultado) => {
          if (!cancelado) setSimulacion(resultado);
        })
        .catch(() => {
          // Fallo transitorio de red -- el panel simplemente no actualiza, nunca
          // bloquea el resto del formulario (mismo criterio que el resto de esta
          // pantalla con llamadas de apoyo, ej. alSalirAclaracionBooleana).
        })
        .finally(() => {
          if (!cancelado) setSimulando(false);
        });
    }, 500);

    return () => {
      cancelado = true;
      clearTimeout(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    tramiteId,
    esperandoPlan,
    valores.documentos_digitalizados,
    valores.motor_pagos,
    valores.firma_electronica_habilitada,
    valores.interoperabilidad,
    mecanismoSeleccion,
  ]);

  function construirRespuestas(): RespuestasDiagnostico {
    const respuestas: RespuestasDiagnostico = {};
    for (const pregunta of preguntasEfectivas) {
      const valor = valores[pregunta.id];
      if (valor !== null) respuestas[pregunta.id] = valor;
    }
    for (const va of variablesAdicionales) {
      const valor = valoresAdicionales[va.variable] ?? null;
      if (valor !== null) respuestas[va.variable] = valor;
    }
    if (volumenDemanda) respuestas.volumen_demanda_anual = volumenDemanda;
    if (tramiteConcurrente !== null) respuestas.tramite_concurrente = tramiteConcurrente;
    if (tramiteConcurrenteDetalle.trim()) respuestas.tramite_concurrente_detalle = tramiteConcurrenteDetalle.trim();
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

  // 409 (el plan de este trámite todavía se está generando) y 429 (cooldown del
  // endpoint de envío) traen un `detail` en lenguaje llano y accionable, distinto
  // para cada caso -- el genérico "intenta de nuevo" es además mal consejo para
  // un 429, donde reintentar de inmediato vuelve a fallar.
  function mensajeDeError(error: unknown): string {
    if (error instanceof ApiError && (error.status === 409 || error.status === 429)) {
      return error.message;
    }
    return "No se pudo completar la operación. Intenta de nuevo.";
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
    setMecanismoErrorClasificacion(false);
    try {
      const { categoria } = await clasificarMecanismoIdentidad(mecanismoAclaracion);
      const reconocida = categoria in ETIQUETA_MECANISMO;
      setMecanismoSugerencia(reconocida ? categoria : null);
      if (!reconocida) setMecanismoErrorClasificacion(true);
    } catch {
      // La clasificación puede fallar por red/timeout -- sin esto el usuario se
      // queda sin ninguna señal de por qué el botón de enviar sigue deshabilitado.
      setMecanismoSugerencia(null);
      setMecanismoErrorClasificacion(true);
    } finally {
      setClasificandoMecanismo(false);
    }
  }

  const todasBooleanasRespondidas = preguntasEfectivas.every((p) => valores[p.id] !== null);
  const todasAdicionalesRespondidas = variablesAdicionales.every(
    (va) => (valoresAdicionales[va.variable] ?? null) !== null,
  );
  const mecanismoResuelto = mecanismoSeleccion !== null && mecanismoSeleccion !== OPCION_OTRO;
  const listoParaEnviar = todasBooleanasRespondidas && todasAdicionalesRespondidas && mecanismoResuelto;

  const totalPreguntas = preguntasEfectivas.length + variablesAdicionales.length + 1;
  const respondidas =
    preguntasEfectivas.filter((p) => valores[p.id] !== null).length +
    variablesAdicionales.filter((va) => (valoresAdicionales[va.variable] ?? null) !== null).length +
    (mecanismoResuelto ? 1 : 0);
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
            <Button variant="outline" onClick={() => void navigate("/")}>
              Volver al panel resumen
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 p-6 lg:grid-cols-[1fr_300px]">
      <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">Cuestionario de diagnóstico</h2>
        <Progress value={avance} />
        <p className="text-xs text-atenuado">
          {respondidas} de {totalPreguntas} preguntas respondidas
        </p>
      </div>

      {preguntasPorSeccion.map(({ seccion, preguntas }) => (
        <div key={seccion} className="flex flex-col gap-4">
          <h3 className="text-sm font-semibold text-muted-foreground">{seccion}</h3>
          {preguntas.map((definicion) => (
            <CardBooleana
              key={definicion.id}
              definicion={definicion}
              valor={valores[definicion.id]}
              aclaracion={aclaraciones[definicion.id] ?? ""}
              sugerencia={sugerencias[definicion.id]}
              clasificando={clasificandoBooleana[definicion.id]}
              onCambiarValor={(valor) => setValores((prev) => ({ ...prev, [definicion.id]: valor }))}
              onCambiarAclaracion={(texto) => setAclaraciones((prev) => ({ ...prev, [definicion.id]: texto }))}
              onSalirAclaracion={() => void alSalirAclaracionBooleana(definicion.id)}
              onConfirmarSugerencia={() => {
                const sugerencia = sugerencias[definicion.id];
                if (sugerencia) {
                  setValores((prev) => ({
                    ...prev,
                    [definicion.id]: sugerencia === "posible_contradiccion_hacia_si",
                  }));
                }
                setSugerencias((prev) => ({ ...prev, [definicion.id]: null }));
              }}
              onDescartarSugerencia={() => setSugerencias((prev) => ({ ...prev, [definicion.id]: null }))}
            />
          ))}
        </div>
      ))}

      {variablesAdicionales.map((va) => (
        <CardVariableAdicional
          key={va.variable}
          pregunta={va.pregunta}
          ayuda={va.ayuda}
          valor={valoresAdicionales[va.variable] ?? null}
          onCambiarValor={(valor) => setValoresAdicionales((prev) => ({ ...prev, [va.variable]: valor }))}
        />
      ))}

      <div className="flex flex-col gap-4">
        <h3 className="text-sm font-semibold text-muted-foreground">Contexto adicional (opcional)</h3>
        <CardVolumenDemanda valor={volumenDemanda} onCambiar={setVolumenDemanda} />
        <CardTramiteConcurrente
          valor={tramiteConcurrente}
          detalle={tramiteConcurrenteDetalle}
          onCambiarValor={setTramiteConcurrente}
          onCambiarDetalle={setTramiteConcurrenteDetalle}
        />
      </div>

      <CardMecanismoIdentidad
        pais={pais}
        seleccion={mecanismoSeleccion}
        aclaracion={mecanismoAclaracion}
        sugerencia={mecanismoSugerencia}
        clasificando={clasificandoMecanismo}
        errorClasificacion={mecanismoErrorClasificacion}
        onCambiarSeleccion={(valor) => {
          setMecanismoSeleccion(valor);
          setMecanismoSugerencia(null);
          setMecanismoErrorClasificacion(false);
        }}
        onCambiarAclaracion={(texto) => {
          setMecanismoAclaracion(texto);
          setMecanismoErrorClasificacion(false);
        }}
        onSalirAclaracion={() => void alSalirAclaracionMecanismo()}
        onConfirmarSugerencia={() => {
          if (mecanismoSugerencia) setMecanismoSeleccion(mecanismoSugerencia);
          setMecanismoSugerencia(null);
        }}
        onDescartarSugerencia={() => setMecanismoSugerencia(null)}
      />

      {(guardarMutacion.isError || enviarMutacion.isError) && (
        <p role="alert" className="text-sm text-destructive">
          {mensajeDeError(enviarMutacion.error ?? guardarMutacion.error)}
        </p>
      )}

      <div className="flex flex-wrap gap-3">
        <Button variant="outline" onClick={() => guardarMutacion.mutate()} disabled={guardarMutacion.isPending}>
          {guardarMutacion.isPending ? "Guardando..." : "Guardar y continuar después"}
        </Button>
        <Button
          onClick={() => enviarMutacion.mutate()}
          disabled={!listoParaEnviar || enviarMutacion.isPending}
          title={
            !listoParaEnviar
              ? mecanismoSeleccion === OPCION_OTRO
                ? "Confirme una sugerencia o seleccione un mecanismo de la lista antes de enviar"
                : "Responda todas las preguntas antes de enviar"
              : undefined
          }
        >
          {enviarMutacion.isPending ? "Enviando..." : "Enviar diagnóstico"}
        </Button>
      </div>
      </div>

      <PanelProyeccion simulacion={simulacion} cargando={simulando} />
    </div>
  );
}

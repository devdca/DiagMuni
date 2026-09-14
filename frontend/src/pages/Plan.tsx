import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { obtenerHistorial, type EventoHistorialResponse } from "@/lib/historialApi";
import { ApiError } from "@/lib/httpClient";
import { obtenerNivelMadurez } from "@/lib/madurez";
import {
  descargarPlanPdf,
  obtenerPlan,
  type Brecha,
  type ComponenteRecomendado,
  type CostoComponente,
  type EstimacionRecursos,
  type MontoDual,
  type OrdenSugerido,
  type ProgresoHistorico,
  type ResumenInversion,
  type ResumenPersonal,
  type SugerenciaLibre,
} from "@/lib/planApi";

// Plan de modernización generado (docs/ux-brief.md sección "4. Plan de modernización
// generado", docs/app-flow.md paso 4): índice actual→objetivo con la misma paleta
// ordinal del panel resumen, párrafo introductorio siempre visible, y un Accordion
// con el desglose completo de cada brecha -- reemplaza el placeholder de F1.

const MARCADOR_NO_VERIFICADO = "[NO VERIFICADO]";
const TEXTO_COSTO_NO_DISPONIBLE = "Costo no verificado: no se encontró una fuente pública confiable";

// El índice objetivo nunca se inventa: backend/app/engine/madurez.py::calcular_indice_madurez
// deja el índice 4 como el único techo alcanzable -- si el plan lista al menos una
// brecha, el objetivo siempre es 4. Si no hay ninguna brecha (docs/app-flow.md,
// "Trámite sin brechas"), el trámite ya está en el máximo alcanzado: actual y
// objetivo son el mismo número, sin flecha.
const INDICE_OBJETIVO = 4;

function valorCosto(valor: string, codigo: string): string | null {
  if (valor === MARCADOR_NO_VERIFICADO) return null;
  return `${valor} ${codigo}`;
}

function FilaCosto({
  etiqueta,
  costo,
  codigoMonedaLocal,
}: {
  etiqueta: string;
  costo: CostoComponente;
  codigoMonedaLocal: string;
}) {
  const local = valorCosto(costo.moneda_local, codigoMonedaLocal);
  const usd = valorCosto(costo.usd, "USD");

  return (
    <p className="text-sm">
      <span className="font-medium">{etiqueta}: </span>
      {local ?? TEXTO_COSTO_NO_DISPONIBLE}
      {usd && <span className="text-muted-foreground"> ({usd})</span>}
    </p>
  );
}

function BloqueComponenteRecomendado({ componente }: { componente: ComponenteRecomendado }) {
  return (
    <div className="flex flex-col gap-2 rounded-md border border-border bg-secondary px-3 py-3">
      <p className="text-sm font-medium">Componente recomendado: {componente.nombre_componente}</p>
      <p className="text-xs text-muted-foreground">Licencia: {componente.licencia}</p>
      <a
        href={componente.url_repositorio}
        target="_blank"
        rel="noreferrer"
        className="text-xs underline underline-offset-2"
      >
        Ver repositorio del componente
      </a>
      <div className="flex flex-col gap-1">
        <FilaCosto
          etiqueta="Costo de licenciamiento"
          costo={componente.costo_licenciamiento}
          codigoMonedaLocal={componente.moneda_local_codigo}
        />
        <FilaCosto
          etiqueta="Costo de infraestructura"
          costo={componente.costo_infraestructura}
          codigoMonedaLocal={componente.moneda_local_codigo}
        />
        <FilaCosto
          etiqueta="Costo de implementación"
          costo={componente.costo_implementacion}
          codigoMonedaLocal={componente.moneda_local_codigo}
        />
      </div>
      {componente.nota_advertencia && (
        <p className="rounded-md border border-border bg-background px-3 py-2 text-xs text-muted-foreground">
          {componente.nota_advertencia}
        </p>
      )}
    </div>
  );
}

function ItemBrecha({ brecha, indice }: { brecha: Brecha; indice: number }) {
  return (
    <AccordionItem value={`${brecha.variable}-${indice}`}>
      <AccordionTrigger>{brecha.narrativa}</AccordionTrigger>
      <AccordionContent>
        <p className="text-sm">
          <span className="font-medium">Paso administrativo: </span>
          {brecha.paso_administrativo}
        </p>
        <p className="text-sm">
          <span className="font-medium">Paso técnico: </span>
          {brecha.paso_tecnico}
        </p>
        <p className="text-sm">
          <span className="font-medium">Paso organizacional: </span>
          {brecha.paso_organizacional}
        </p>

        {brecha.prerrequisitos.length > 0 && (
          <div className="text-sm">
            <p className="font-medium">Prerrequisitos:</p>
            <ul className="list-disc pl-5">
              {brecha.prerrequisitos.map((prerrequisito) => (
                <li key={prerrequisito}>{prerrequisito}</li>
              ))}
            </ul>
          </div>
        )}

        <p className="text-xs text-muted-foreground">Fuente normativa: {brecha.fuente_normativa}</p>

        {brecha.componente_recomendado && <BloqueComponenteRecomendado componente={brecha.componente_recomendado} />}
      </AccordionContent>
    </AccordionItem>
  );
}

// Siempre visualmente distinta de las brechas verificadas (borde/fondo de aviso,
// no de tarjeta normal) -- nunca debe confundirse con un hallazgo del catálogo
// legal, ver backend/app/ia/sugerencia_libre.py.
function TarjetaSugerenciaLibre({ sugerencia }: { sugerencia: SugerenciaLibre }) {
  return (
    <Card className="border-amber-500/50 bg-amber-500/5">
      <CardHeader>
        <CardTitle className="text-base">Sugerencia a partir de tu descripción</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm">{sugerencia.texto}</p>
        <p className="text-xs font-medium text-amber-600 dark:text-amber-400">{sugerencia.advertencia}</p>
      </CardContent>
    </Card>
  );
}

// Mismo criterio que TarjetaSugerenciaLibre -- estimación de IA, no verificada,
// ver backend/app/ia/estimacion_recursos.py.
function TarjetaEstimacionRecursos({ estimacion }: { estimacion: EstimacionRecursos }) {
  return (
    <Card className="border-amber-500/50 bg-amber-500/5">
      <CardHeader>
        <CardTitle className="text-base">Estimación aproximada de personal y presupuesto</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm">{estimacion.texto}</p>
        <p className="text-xs font-medium text-amber-600 dark:text-amber-400">{estimacion.advertencia}</p>
      </CardContent>
    </Card>
  );
}

// --- Tarjetas de la pestaña "Resumen ejecutivo" -------------------------------------

function textoMontoDual(monto: MontoDual, codigoMonedaLocal: string): string {
  if (monto.moneda_local === null) return "Sin dato verificado";
  return monto.usd ? `${monto.moneda_local} ${codigoMonedaLocal} (${monto.usd} USD)` : `${monto.moneda_local} ${codigoMonedaLocal}`;
}

function TarjetaPresupuesto({ resumen }: { resumen: ResumenInversion }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Presupuesto estimado</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm">
          <span className="font-medium">Inversión única estimada: </span>
          {textoMontoDual(resumen.inversion_unica_estimada, resumen.moneda_local_codigo)}
        </p>
        <p className="text-sm">
          <span className="font-medium">Costo recurrente mensual estimado: </span>
          {textoMontoDual(resumen.costo_recurrente_mensual_estimado, resumen.moneda_local_codigo)}
        </p>
        <p className="text-xs text-muted-foreground">
          {resumen.brechas_con_componente_software} de {resumen.brechas_totales} brecha(s) tienen un componente de
          software identificado en el catálogo.
        </p>
        {resumen.componentes.length > 0 && (
          <div className="flex flex-col gap-3">
            {resumen.componentes.map((componente) => (
              <BloqueComponenteRecomendado key={componente.nombre_componente} componente={componente} />
            ))}
          </div>
        )}
        <p className="text-xs text-muted-foreground">{resumen.nota_cobertura}</p>
      </CardContent>
    </Card>
  );
}

function TarjetaPersonal({ resumen }: { resumen: ResumenPersonal }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Personal y capacitación</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-col gap-1 text-sm">
          <p>
            <span className="font-medium">Personal actual del área de TI: </span>
            {resumen.personal_ti_actual ?? "No capturado en el perfil de gobierno"}
          </p>
          <p>
            <span className="font-medium">Personal total del gobierno: </span>
            {resumen.personal_total_gobierno ?? "No capturado en el perfil de gobierno"}
          </p>
          <p>
            <span className="font-medium">¿Capacitación digital anual vigente?: </span>
            {resumen.capacitacion_anual_vigente === null
              ? "No capturado en el perfil de gobierno"
              : resumen.capacitacion_anual_vigente
                ? "Sí"
                : "No"}
          </p>
          {resumen.costo_referencia_personal_ti && (
            <p>
              <span className="font-medium">Costo de referencia de 1 puesto de TI: </span>
              {resumen.costo_referencia_personal_ti.salario_mensual_promedio === "[NO VERIFICADO]"
                ? "Sin fuente oficial verificada para este país"
                : `${resumen.costo_referencia_personal_ti.salario_mensual_promedio} ${resumen.costo_referencia_personal_ti.moneda}/mes (${resumen.costo_referencia_personal_ti.puesto_referencia})`}
            </p>
          )}
        </div>
        {resumen.acciones_organizacionales.length > 0 && (
          <div className="text-sm">
            <p className="font-medium">Acciones organizacionales requeridas:</p>
            <ul className="list-disc pl-5">
              {resumen.acciones_organizacionales.map((accion) => (
                <li key={accion}>{accion}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function TarjetaProgresoHistorico({ progreso }: { progreso: ProgresoHistorico }) {
  if (progreso.brechas_resueltas.length === 0 && progreso.brechas_nuevas.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Progreso desde el diagnóstico anterior</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {progreso.brechas_resueltas.length > 0 && (
          <div className="rounded-md border border-emerald-500/50 bg-emerald-500/5 px-3 py-2 text-sm">
            <p className="font-medium text-emerald-700 dark:text-emerald-400">
              {progreso.brechas_resueltas.length} brecha(s) resuelta(s) desde el diagnóstico anterior
            </p>
            <ul className="list-disc pl-5">
              {progreso.brechas_resueltas.map((variable) => (
                <li key={variable}>{variable}</li>
              ))}
            </ul>
          </div>
        )}
        {progreso.brechas_nuevas.length > 0 && (
          <div className="rounded-md border border-amber-500/50 bg-amber-500/5 px-3 py-2 text-sm">
            <p className="font-medium text-amber-700 dark:text-amber-400">
              {progreso.brechas_nuevas.length} brecha(s) nueva(s) desde el diagnóstico anterior
            </p>
            <ul className="list-disc pl-5">
              {progreso.brechas_nuevas.map((variable) => (
                <li key={variable}>{variable}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ListaBrechasCorta({ brechas }: { brechas: Brecha[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Brechas detectadas</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="flex flex-col gap-2">
          {brechas.map((brecha) => (
            <li key={brecha.variable} className="text-sm">
              <span className="font-medium">{brecha.categoria_catalogo}: </span>
              {brecha.narrativa}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

// Ordena por `orden_sugerido` (backend/app/engine/resumen_plan.py) -- brechas sin
// prerrequisitos pendientes primero. No es un grafo de dependencias real, es la
// lectura de lo que `prerrequisitos` ya declara por brecha (texto libre).
function brechasEnOrdenSugerido(brechas: Brecha[], orden: OrdenSugerido): Brecha[] {
  const porVariable = new Map(brechas.map((b) => [b.variable, b]));
  const ordenadas = [...orden.sin_prerrequisitos, ...orden.con_prerrequisitos]
    .map((variable) => porVariable.get(variable))
    .filter((b): b is Brecha => b !== undefined);
  // Defensivo: cualquier brecha que por algún motivo no aparezca en `orden` (no
  // debería pasar, se calcula sobre las mismas `brechas`) se agrega al final en
  // vez de desaparecer silenciosamente.
  const variablesOrdenadas = new Set(ordenadas.map((b) => b.variable));
  return [...ordenadas, ...brechas.filter((b) => !variablesOrdenadas.has(b.variable))];
}

function EncabezadoIndice({ actual, sinBrechas }: { actual: number; sinBrechas: boolean }) {
  const nivelActual = obtenerNivelMadurez(actual);
  const nivelObjetivo = obtenerNivelMadurez(INDICE_OBJETIVO);

  return (
    <div className="flex items-center gap-4">
      <div className="flex flex-col items-center">
        <span className="text-4xl font-semibold tabular-nums" style={{ color: nivelActual.varTexto }}>
          {nivelActual.nivel}
        </span>
        <span className="text-xs text-muted-foreground">{nivelActual.etiqueta}</span>
      </div>
      {!sinBrechas && (
        <>
          <span aria-hidden className="text-2xl text-muted-foreground">
            →
          </span>
          <div className="flex flex-col items-center">
            <span className="text-4xl font-semibold tabular-nums" style={{ color: nivelObjetivo.varTexto }}>
              {nivelObjetivo.nivel}
            </span>
            <span className="text-xs text-muted-foreground">{nivelObjetivo.etiqueta}</span>
          </div>
        </>
      )}
    </div>
  );
}

// --- Pestaña "Historial" -- línea de tiempo persistida del trámite ------------------
//
// Consulta propia (no viaja en PlanOut): se monta solo cuando la pestaña está
// activa (Radix Tabs no renderiza TabsContent inactivo por defecto), así que no
// agrega una llamada extra al cargar la pantalla si el funcionario nunca la abre.

function tituloEvento(tipo: string): string {
  const titulos: Record<string, string> = {
    diagnostico_enviado: "Diagnóstico enviado",
    diagnostico_corregido: "Diagnóstico corregido",
    plan_generado: "Plan generado",
    accion_actualizada: "Acción de seguimiento actualizada",
    tramite_archivado: "Trámite archivado",
    tramite_desarchivado: "Trámite desarchivado",
  };
  return titulos[tipo] ?? tipo;
}

function formatearFechaHora(fechaIso: string): string {
  return new Date(fechaIso).toLocaleString("es", { year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function FilaHistorial({ evento }: { evento: EventoHistorialResponse }) {
  return (
    <li className="relative border-l border-border pb-6 pl-5 last:pb-0">
      <span aria-hidden className="absolute top-1 -left-[5px] size-2.5 rounded-full bg-primary" />
      <p className="text-xs text-atenuado">{formatearFechaHora(evento.creado_en)}</p>
      <p className="text-sm font-medium">{tituloEvento(evento.tipo)}</p>
      <p className="text-sm text-muted-foreground">{evento.descripcion}</p>
    </li>
  );
}

function TarjetaHistorial({ tramiteId }: { tramiteId: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["historial", tramiteId],
    queryFn: () => obtenerHistorial(tramiteId),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Historial del trámite</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && <p className="text-sm text-atenuado">Cargando...</p>}
        {isError && <p className="text-sm text-destructive">No se pudo cargar el historial.</p>}
        {data && data.length === 0 && (
          <p className="text-sm text-muted-foreground">Todavía no hay eventos registrados para este trámite.</p>
        )}
        {data && data.length > 0 && (
          <ul className="flex flex-col">
            {data.map((evento) => (
              <FilaHistorial key={evento.id} evento={evento} />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export function Plan() {
  const { tramiteId } = useParams<{ tramiteId: string }>();
  const navigate = useNavigate();
  const [descargando, setDescargando] = useState(false);
  const [errorDescarga, setErrorDescarga] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["plan", tramiteId],
    queryFn: () => obtenerPlan(tramiteId!),
    enabled: !!tramiteId,
    retry: (intentosPrevios, error) => {
      if (error instanceof ApiError && error.status === 404) return false;
      return intentosPrevios < 3;
    },
  });

  if (!tramiteId) return null;

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-sm text-atenuado">Cargando...</p>
      </div>
    );
  }

  if (error instanceof ApiError && error.status === 404) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4 p-6">
        <Card>
          <CardHeader>
            <CardTitle>Plan aún no generado</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <p className="text-sm text-muted-foreground">
              Todavía no existe un plan de modernización para este trámite. Primero complete y envíe el diagnóstico.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button onClick={() => void navigate(`/tramites/${tramiteId}/diagnostico`)}>Ir al diagnóstico</Button>
              <Button variant="outline" onClick={() => void navigate("/")}>
                Volver al panel resumen
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4 p-6">
        <Card>
          <CardHeader>
            <CardTitle>No se pudo cargar el plan</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <p className="text-sm text-destructive">No se pudo completar la operación. Intenta de nuevo.</p>
            <Button variant="outline" onClick={() => void navigate("/")}>
              Volver al panel resumen
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const brechas = data.contenido.brechas;
  const sinBrechas = brechas.length === 0;
  const brechasOrdenadas = brechasEnOrdenSugerido(brechas, data.contenido.orden_sugerido);

  async function alDescargarPdf() {
    setDescargando(true);
    setErrorDescarga(false);
    try {
      await descargarPlanPdf(tramiteId!);
    } catch {
      setErrorDescarga(true);
    } finally {
      setDescargando(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle>Plan de modernización</CardTitle>
          <div className="flex flex-col items-end gap-1">
            <div className="flex gap-2">
              {data.version > 1 && (
                <Button variant="outline" onClick={() => void navigate(`/tramites/${tramiteId}/plan/comparar`)}>
                  Comparar versiones
                </Button>
              )}
              <Button variant="outline" onClick={() => void alDescargarPdf()} disabled={descargando}>
                {descargando ? "Generando PDF..." : "Descargar PDF"}
              </Button>
            </div>
            {errorDescarga && (
              <p role="alert" className="text-xs text-destructive">
                No se pudo generar el PDF. Intenta de nuevo.
              </p>
            )}
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {data.indice_madurez === null ? (
            <p className="text-sm text-muted-foreground">Índice de madurez no disponible para este trámite.</p>
          ) : (
            <EncabezadoIndice actual={data.indice_madurez} sinBrechas={sinBrechas} />
          )}

          {data.modo === "degradado" && (
            <p className="rounded-md border border-border bg-secondary px-4 py-3 text-sm">
              Este plan se generó con nuestras plantillas internas, sin asistencia de redacción por inteligencia
              artificial disponible en este momento. Es un plan igual de válido: las acciones, la normativa y los
              componentes recomendados siguen los mismos criterios en cualquier caso.
            </p>
          )}

          <p className="text-sm text-muted-foreground">{data.contenido.resumen_narrativo}</p>
        </CardContent>
      </Card>

      <Tabs defaultValue="ejecutivo">
        <TabsList>
          <TabsTrigger value="ejecutivo">Resumen ejecutivo</TabsTrigger>
          <TabsTrigger value="tecnico">Detalle técnico</TabsTrigger>
          <TabsTrigger value="historial">Historial</TabsTrigger>
        </TabsList>

        <TabsContent value="ejecutivo">
          {data.progreso_historico && <TarjetaProgresoHistorico progreso={data.progreso_historico} />}
          <TarjetaPresupuesto resumen={data.contenido.resumen_inversion} />
          <TarjetaPersonal resumen={data.contenido.resumen_personal} />
          {data.contenido.estimacion_recursos && (
            <TarjetaEstimacionRecursos estimacion={data.contenido.estimacion_recursos} />
          )}
          {data.contenido.sugerencia_libre && <TarjetaSugerenciaLibre sugerencia={data.contenido.sugerencia_libre} />}
          {!sinBrechas && <ListaBrechasCorta brechas={brechasOrdenadas} />}
        </TabsContent>

        <TabsContent value="tecnico">
          {!sinBrechas && (
            <Card>
              <CardHeader>
                <CardTitle>Detalle por brecha (verificado)</CardTitle>
              </CardHeader>
              <CardContent>
                <Accordion type="multiple">
                  {brechasOrdenadas.map((brecha, indice) => (
                    <ItemBrecha key={`${brecha.variable}-${indice}`} brecha={brecha} indice={indice} />
                  ))}
                </Accordion>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="historial">
          <TarjetaHistorial tramiteId={tramiteId} />
        </TabsContent>
      </Tabs>

      <Button variant="outline" onClick={() => void navigate("/seguimiento")}>
        Ir al seguimiento
      </Button>
    </div>
  );
}

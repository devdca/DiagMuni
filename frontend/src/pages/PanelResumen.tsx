import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GraficaTendenciaIndice } from "@/components/GraficaTendenciaIndice";
import { HeroIndiceGlobal } from "@/components/HeroIndiceGlobal";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { obtenerNivelMadurez } from "@/lib/madurez";
import { obtenerPais } from "@/lib/session";
import { listarAccionesSeguimiento, type AccionSeguimientoResponse } from "@/lib/seguimientoApi";

import {
  archivarTramite,
  crearTramite,
  desarchivarTramite,
  eliminarTramite,
  obtenerHistorialIndiceGlobal,
  obtenerPanelResumen,
  obtenerTiposTramite,
  type EstadoTramite,
  type TramiteResponse,
} from "../lib/tramitesApi";

// Panel de control: índice de madurez global con tendencia real, avance del
// catálogo, acciones atrasadas, prioridades de la semana y la tabla de
// trámites. Nunca muestra un número que no salga de datos reales.

const NOMBRE_PAIS: Record<string, string> = { mx: "México", uy: "Uruguay" };

const ETIQUETA_ESTADO_TRAMITE: Record<EstadoTramite, string> = {
  sin_iniciar: "Sin iniciar",
  en_progreso: "En progreso",
  diagnosticado: "Diagnosticado",
  generando_plan: "Generando plan",
  plan_listo: "Plan listo",
};

function formatearFecha(fechaIso: string): string {
  return new Date(fechaIso).toLocaleDateString("es", { year: "numeric", month: "long", day: "numeric" });
}

// "Última actividad": relativo mientras es reciente, fecha completa si ya
// pasó más de un mes (un número de semanas grande no se escanea rápido).
function formatearActividad(fechaIso: string): string {
  const dias = Math.floor((Date.now() - new Date(fechaIso).getTime()) / 86_400_000);
  if (dias <= 0) return "hoy";
  if (dias === 1) return "hace 1 día";
  if (dias < 7) return `hace ${dias} días`;
  const semanas = Math.floor(dias / 7);
  if (semanas === 1) return "hace 1 semana";
  if (semanas < 5) return `hace ${semanas} semanas`;
  return formatearFecha(fechaIso);
}

function formatearPlazo(fechaObjetivoIso: string, atrasado: boolean): string {
  const dias = Math.round((new Date(fechaObjetivoIso).getTime() - Date.now()) / 86_400_000);
  if (atrasado) {
    const diasVencido = Math.abs(dias);
    return diasVencido <= 0 ? "Vence hoy" : `Venció hace ${diasVencido} ${diasVencido === 1 ? "día" : "días"}`;
  }
  if (dias <= 0) return "Vence hoy";
  return `Vence en ${dias} ${dias === 1 ? "día" : "días"}`;
}

function BadgeIndice({ indice }: { indice: number | null }) {
  if (indice === null) {
    return <Badge variant="outline">Sin diagnosticar</Badge>;
  }
  const nivel = obtenerNivelMadurez(indice);
  return (
    <Badge variant="outline" style={{ borderColor: nivel.varTexto, color: nivel.varTexto }}>
      <span aria-hidden className="inline-block size-2 rounded-full" style={{ backgroundColor: nivel.hexClaro }} />
      {nivel.nivel} — {nivel.etiqueta}
    </Badge>
  );
}

function AccionTramite({ tramite }: { tramite: TramiteResponse }) {
  const navigate = useNavigate();

  if (tramite.estado === "sin_iniciar" || tramite.estado === "en_progreso") {
    return (
      <Button size="sm" onClick={() => void navigate(`/tramites/${tramite.id}/diagnostico`)}>
        Continuar diagnóstico
      </Button>
    );
  }

  if (tramite.estado === "plan_listo") {
    return (
      <div className="flex justify-end gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={() => void navigate(`/tramites/${tramite.id}/diagnostico`)}
        >
          Corregir respuestas
        </Button>
        <Button size="sm" onClick={() => void navigate(`/tramites/${tramite.id}/plan`)}>
          Ver plan
        </Button>
      </div>
    );
  }

  // "diagnosticado"/"generando_plan": el plan ya se genera solo, sin acción
  // manual pendiente -- texto de espera en vez de un botón que sugiera lo contrario.
  return <span className="text-sm text-atenuado">Generando plan de modernización...</span>;
}

// Confirmación inline de dos pasos en vez de `window.confirm` -- ese diálogo
// nativo no se muestra bajo automatización/testing, dejando el botón "sin efecto".
function BotonEliminar({ tramite, disabled, onEliminar }: { tramite: TramiteResponse; disabled: boolean; onEliminar: () => void }) {
  const [confirmando, setConfirmando] = useState(false);

  if (confirmando) {
    return (
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-atenuado">¿Eliminar "{tramite.nombre}"?</span>
        <Button size="sm" variant="destructive" disabled={disabled} onClick={onEliminar}>
          Sí, eliminar
        </Button>
        <Button size="sm" variant="outline" onClick={() => setConfirmando(false)}>
          Cancelar
        </Button>
      </div>
    );
  }

  return (
    <Button size="sm" variant="outline" disabled={disabled} onClick={() => setConfirmando(true)}>
      Eliminar
    </Button>
  );
}

// Gestión de un trámite: eliminar (borrado físico, solo si no está completado)
// o archivar/desarchivar (reversible, oculta del panel sin borrar nada).
function AccionesGestion({ tramite, archivados }: { tramite: TramiteResponse; archivados: boolean }) {
  const queryClient = useQueryClient();
  const invalidar = () => void queryClient.invalidateQueries({ queryKey: ["panel-resumen"] });

  const eliminarMutacion = useMutation({ mutationFn: eliminarTramite, onSuccess: invalidar });
  const archivarMutacion = useMutation({ mutationFn: archivarTramite, onSuccess: invalidar });
  const desarchivarMutacion = useMutation({ mutationFn: desarchivarTramite, onSuccess: invalidar });

  if (archivados) {
    return (
      <Button
        size="sm"
        variant="outline"
        disabled={desarchivarMutacion.isPending}
        onClick={() => desarchivarMutacion.mutate(tramite.id)}
      >
        Desarchivar
      </Button>
    );
  }

  return (
    <div className="flex justify-end gap-2">
      {tramite.completado_en === null && (
        <BotonEliminar
          tramite={tramite}
          disabled={eliminarMutacion.isPending}
          onEliminar={() => eliminarMutacion.mutate(tramite.id)}
        />
      )}
      <Button
        size="sm"
        variant="outline"
        disabled={archivarMutacion.isPending}
        onClick={() => archivarMutacion.mutate(tramite.id)}
      >
        Archivar
      </Button>
    </div>
  );
}

// Alta de un trámite en el catálogo -- formulario simple, sin modal, mismo
// criterio de "sin metodologías pesadas" que el resto del panel.
function FormularioNuevoTramite({
  abierto,
  onCerrar,
  tipos,
}: {
  abierto: boolean;
  onCerrar: () => void;
  tipos: { nombre: string; etiqueta: string }[];
}) {
  const queryClient = useQueryClient();
  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [tipo, setTipo] = useState("generico");

  const crearMutacion = useMutation({
    mutationFn: crearTramite,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["panel-resumen"] });
      setNombre("");
      setDescripcion("");
      setTipo("generico");
      onCerrar();
    },
  });

  if (!abierto) return null;

  return (
    <form
      className="mb-4 flex flex-col gap-3 rounded-md border border-border p-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (nombre.trim() === "") return;
        crearMutacion.mutate({ nombre: nombre.trim(), descripcion: descripcion.trim(), tipo });
      }}
    >
      <div className="flex flex-col gap-2">
        <label htmlFor="nuevo-tramite-nombre" className="text-sm font-medium">
          Nombre del trámite
        </label>
        <Input
          id="nuevo-tramite-nombre"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Ej. Licencia de funcionamiento"
          // Tope de 150 (el backend es la fuente de verdad real) -- sin esto, un
          // nombre larguísimo rompía la tabla de trámites (QA ronda 2).
          maxLength={150}
          required
        />
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor="nuevo-tramite-tipo" className="text-sm font-medium">
          Tipo de trámite
        </label>
        <select
          id="nuevo-tramite-tipo"
          value={tipo}
          onChange={(e) => setTipo(e.target.value)}
          className="min-h-[44px] rounded-md border border-input bg-background px-2 text-sm text-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          {tipos.map((t) => (
            <option key={t.nombre} value={t.nombre}>
              {t.etiqueta}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor="nuevo-tramite-descripcion" className="text-sm font-medium">
          Descripción (opcional)
        </label>
        <Textarea
          id="nuevo-tramite-descripcion"
          value={descripcion}
          onChange={(e) => setDescripcion(e.target.value)}
        />
      </div>
      {crearMutacion.isError && (
        <p className="text-xs text-destructive">No se pudo agregar el trámite. Intenta de nuevo.</p>
      )}
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={crearMutacion.isPending}>
          {crearMutacion.isPending ? "Guardando..." : "Guardar"}
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={onCerrar}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}

// Anillo de avance (decorativo, aria-hidden) -- el número real siempre se
// muestra como texto al lado, nunca solo el dibujo.
function AnilloAvance({ porcentaje }: { porcentaje: number }) {
  const radio = 28;
  const circunferencia = 2 * Math.PI * radio;
  const relleno = (Math.max(0, Math.min(100, porcentaje)) / 100) * circunferencia;
  return (
    <svg aria-hidden width="64" height="64" viewBox="0 0 68 68">
      <circle cx="34" cy="34" r={radio} fill="none" stroke="var(--muted)" strokeWidth="8" />
      <circle
        cx="34"
        cy="34"
        r={radio}
        fill="none"
        stroke="var(--primary)"
        strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={`${relleno} ${circunferencia}`}
        transform="rotate(-90 34 34)"
      />
    </svg>
  );
}

// Delta contra el punto de hace ~3 meses -- si no hay esa antigüedad de datos,
// simplemente no se muestra la línea, en vez de inventar un "+0.0".
function calcularDeltaTrimestre(
  puntos: { indice_global: number; creado_en: string }[],
  indiceActual: number,
): number | null {
  const haceNoventaDias = Date.now() - 90 * 24 * 60 * 60 * 1000;
  const anteriores = puntos.filter((p) => new Date(p.creado_en).getTime() <= haceNoventaDias);
  if (anteriores.length === 0) return null;
  return indiceActual - anteriores[anteriores.length - 1].indice_global;
}

function obtenerPrioridades(acciones: AccionSeguimientoResponse[]): AccionSeguimientoResponse[] {
  const porFecha = (a: AccionSeguimientoResponse, b: AccionSeguimientoResponse) =>
    new Date(a.fecha_objetivo).getTime() - new Date(b.fecha_objetivo).getTime();
  const atrasadas = acciones.filter((a) => a.estado_semaforo === "atrasado").sort(porFecha);
  const enProgreso = acciones.filter((a) => a.estado_semaforo === "en_progreso").sort(porFecha);
  return [...atrasadas, ...enProgreso].slice(0, 3);
}

export function PanelResumen() {
  const [verArchivados, setVerArchivados] = useState(false);
  // `verArchivados` en el query key: son dos listas mutuamente excluyentes, no
  // una misma lista filtrada en el cliente.
  const { data, isLoading, isError } = useQuery({
    queryKey: ["panel-resumen", verArchivados],
    queryFn: () => obtenerPanelResumen(verArchivados),
  });
  const historialQuery = useQuery({ queryKey: ["historial-indice-global"], queryFn: obtenerHistorialIndiceGlobal });
  const seguimientoQuery = useQuery({ queryKey: ["seguimiento"], queryFn: listarAccionesSeguimiento });
  const tiposQuery = useQuery({ queryKey: ["tipos-tramite"], queryFn: obtenerTiposTramite });
  const [formularioAbierto, setFormularioAbierto] = useState(false);

  const nombreTipo = (tipo: string) => tiposQuery.data?.find((t) => t.nombre === tipo)?.etiqueta ?? tipo;

  const diagnosticados = data ? data.tramites.filter((t) => t.indice_madurez !== null).length : 0;
  const totalActivos = data?.tramites.length ?? 0;
  const porcentajeDiagnosticado = totalActivos > 0 ? Math.round((diagnosticados / totalActivos) * 100) : 0;

  const acciones = seguimientoQuery.data ?? [];
  const accionesActivas = acciones.filter((a) => a.estado_semaforo !== "completado");
  const accionesAtrasadas = accionesActivas.filter((a) => a.estado_semaforo === "atrasado");
  const prioridades = obtenerPrioridades(acciones);

  const delta =
    data?.indice_global !== null && data?.indice_global !== undefined && historialQuery.data
      ? calcularDeltaTrimestre(historialQuery.data, data.indice_global)
      : null;

  return (
    <div className="mx-auto flex max-w-[1360px] flex-col gap-5 p-6">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <PageHeader
          icon={
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round">
              <path d="M4 19V10" />
              <path d="M12 19V5" />
              <path d="M20 19v-7" />
            </svg>
          }
          kicker={NOMBRE_PAIS[obtenerPais() ?? ""] ?? ""}
          title="Panel de control"
        />
        {(!data || verArchivados) && (
          <span className="text-sm text-atenuado">
            {data?.fecha_ultimo_diagnostico
              ? `Último diagnóstico: ${formatearFecha(data.fecha_ultimo_diagnostico)}`
              : "Aún no hay ningún diagnóstico completado"}
          </span>
        )}
      </div>

      {isLoading && <p className="text-sm text-atenuado">Cargando...</p>}
      {isError && <p className="text-sm text-destructive">No se pudo cargar el panel de control.</p>}

      {data && !verArchivados && (
        <HeroIndiceGlobal
          pais={NOMBRE_PAIS[obtenerPais() ?? ""] ?? ""}
          indiceGlobal={data.indice_global}
          delta={delta}
          fechaUltimoDiagnostico={data.fecha_ultimo_diagnostico}
          historial={historialQuery.data ?? []}
        />
      )}

      {data && !verArchivados && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card>
            <CardContent className="flex flex-col gap-2 pt-6">
              <p className="text-xs font-semibold tracking-wide text-atenuado uppercase">Trámites diagnosticados</p>
              <div className="flex items-center gap-4">
                <AnilloAvance porcentaje={porcentajeDiagnosticado} />
                <div>
                  <div className="text-2xl font-bold tabular-nums">
                    {diagnosticados}
                    <span className="text-sm font-medium text-muted-foreground"> / {totalActivos}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">{porcentajeDiagnosticado}% del catálogo</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex flex-col gap-2 pt-6">
              <div className="flex items-center justify-between gap-3">
                <div className="flex flex-col gap-2">
                  <p className="text-xs font-semibold tracking-wide text-atenuado uppercase">Acciones atrasadas</p>
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-bold tabular-nums" style={{ color: "var(--semaforo-atrasado)" }}>
                      {accionesAtrasadas.length}
                    </span>
                    <span className="text-sm text-muted-foreground">de {accionesActivas.length} activas</span>
                  </div>
                  <Link to="/seguimiento" className="text-sm font-semibold text-primary">
                    Ver en seguimiento →
                  </Link>
                </div>
                {/* Decorativo (aria-hidden) -- el dato ya se muestra como texto a la izquierda. */}
                <span
                  aria-hidden
                  className="flex size-14 shrink-0 items-center justify-center rounded-full border-2 text-lg font-bold tabular-nums"
                  style={{
                    borderColor: "var(--semaforo-atrasado)",
                    color: "var(--semaforo-atrasado)",
                  }}
                >
                  {accionesAtrasadas.length}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {data && !verArchivados && (
        <div className="grid grid-cols-1 items-stretch gap-4 lg:grid-cols-[2fr_1fr]">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Tendencia del índice de madurez</CardTitle>
            </CardHeader>
            <CardContent>
              <GraficaTendenciaIndice />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Prioridades de esta semana</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {seguimientoQuery.isLoading && <p className="text-sm text-atenuado">Cargando...</p>}
              {!seguimientoQuery.isLoading && prioridades.length === 0 && (
                <p className="text-sm text-atenuado">No hay acciones atrasadas ni en progreso por ahora.</p>
              )}
              {prioridades.map((accion) => (
                <div key={accion.id} className="flex items-start gap-2.5">
                  <span
                    aria-hidden
                    className="mt-1.5 size-2 shrink-0 rounded-full"
                    style={{
                      backgroundColor:
                        accion.estado_semaforo === "atrasado"
                          ? "var(--semaforo-atrasado)"
                          : "var(--semaforo-en-progreso)",
                    }}
                  />
                  <div className="flex flex-col">
                    <span className="text-sm font-medium">{accion.descripcion}</span>
                    <span className="text-xs text-muted-foreground">
                      {accion.tramite_nombre} · {accion.responsable}
                    </span>
                    <span
                      className="mt-0.5 text-xs font-semibold"
                      style={{
                        color:
                          accion.estado_semaforo === "atrasado" ? "var(--semaforo-atrasado)" : "var(--atenuado)",
                      }}
                    >
                      {formatearPlazo(accion.fecha_objetivo, accion.estado_semaforo === "atrasado")}
                    </span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle>{verArchivados ? "Trámites archivados" : "Trámites catalogados"}</CardTitle>
          <div className="flex gap-2">
            {!verArchivados && !formularioAbierto && (
              <Button size="sm" variant="outline" onClick={() => setFormularioAbierto(true)}>
                Agregar trámite
              </Button>
            )}
            <Button size="sm" variant="outline" onClick={() => setVerArchivados((actual) => !actual)}>
              {verArchivados ? "Ver activos" : "Ver archivados"}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {!verArchivados && (
            <FormularioNuevoTramite
              abierto={formularioAbierto}
              onCerrar={() => setFormularioAbierto(false)}
              tipos={tiposQuery.data ?? []}
            />
          )}
          {verArchivados && data?.tramites.length === 0 && (
            <p className="text-sm text-atenuado">No hay ningún trámite archivado.</p>
          )}
          {/* Sin esto, una ventana angosta hacía scrollear toda la página, no solo la tabla. */}
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th className="py-2 font-medium">Trámite</th>
                  <th className="py-2 font-medium">Tipo</th>
                  <th className="py-2 font-medium">Índice</th>
                  {!verArchivados && <th className="py-2 font-medium">Estado</th>}
                  <th className="py-2 font-medium">Última actividad</th>
                  {!verArchivados && <th className="py-2 font-medium">Acción</th>}
                  <th className="py-2 pr-0 text-right font-medium">Gestión</th>
                </tr>
              </thead>
              <tbody>
                {data?.tramites.map((tramite) => (
                  <tr key={tramite.id} className="border-b border-border last:border-0">
                    <td className="py-3 pr-4 font-medium">{tramite.nombre}</td>
                    <td className="py-3 pr-4 text-muted-foreground">{nombreTipo(tramite.tipo)}</td>
                    <td className="py-3 pr-4">
                      <BadgeIndice indice={tramite.indice_madurez} />
                    </td>
                    {!verArchivados && (
                      <td className="py-3 pr-4">
                        <Badge variant="secondary">{ETIQUETA_ESTADO_TRAMITE[tramite.estado]}</Badge>
                      </td>
                    )}
                    <td className="py-3 pr-4 text-muted-foreground">{formatearActividad(tramite.updated_at)}</td>
                    {!verArchivados && (
                      <td className="py-3 pr-4">
                        <AccionTramite tramite={tramite} />
                      </td>
                    )}
                    <td className="py-3 text-right">
                      <AccionesGestion tramite={tramite} archivados={verArchivados} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

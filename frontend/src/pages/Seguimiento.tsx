import { useEffect, useMemo, useState } from "react";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ESTADOS_SEMAFORO, ORDEN_ESTADOS_SEMAFORO, type EstadoSemaforo } from "@/lib/semaforo";
import {
  actualizarAccionSeguimiento,
  agregarNotaAAccion,
  listarAccionesSeguimiento,
  listarNotasDeAccion,
  type AccionSeguimientoResponse,
  type ActualizarAccionSeguimientoPayload,
} from "@/lib/seguimientoApi";

// Panel de seguimiento (docs/ux-brief.md sección "5. Panel de seguimiento",
// docs/app-flow.md paso 5): tabla simple de todas las acciones de todos los
// trámites con plan generado, con edición inline de responsable/fecha objetivo/
// semáforo directamente en la fila -- sin Gantt, sin dependencias entre tareas,
// sin ningún campo adicional a los 4 ya definidos (mandato explícito de "nada de
// metodologías pesadas"). Clic en la fila navega al plan del trámite de esa
// acción; los controles de edición y el expandir de notas detienen la
// propagación del clic.
//
// Filtros (búsqueda, estado, responsable): puramente del lado del cliente sobre
// la lista ya cargada -- `GET /api/seguimiento` ya trae todas las acciones
// vigentes del tenant (RLS), no hace falta un endpoint nuevo para esto.

const TODOS = "__todos__";

function BadgeSemaforo({ estado }: { estado: EstadoSemaforo }) {
  const info = ESTADOS_SEMAFORO[estado];
  return (
    <Badge variant="outline" style={{ borderColor: info.hex }}>
      <span aria-hidden className="inline-block size-2 rounded-full" style={{ backgroundColor: info.hex }} />
      <span aria-hidden style={{ color: info.hex }}>{info.icono}</span>
      <span>{info.etiqueta}</span>
    </Badge>
  );
}

function SelectorSemaforo({
  valor,
  onCambiar,
}: {
  valor: EstadoSemaforo;
  onCambiar: (valor: EstadoSemaforo) => void;
}) {
  return (
    <select
      aria-label="Cambiar estado del semáforo"
      value={valor}
      onClick={(evento) => evento.stopPropagation()}
      onChange={(evento) => onCambiar(evento.target.value as EstadoSemaforo)}
      className="min-h-[44px] rounded-md border border-input bg-background px-2 text-sm text-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
    >
      {ORDEN_ESTADOS_SEMAFORO.map((opcion) => (
        <option key={opcion} value={opcion}>
          {ESTADOS_SEMAFORO[opcion].etiqueta}
        </option>
      ))}
    </select>
  );
}

function CampoTextoInline({
  valorInicial,
  onGuardar,
  type = "text",
}: {
  valorInicial: string;
  onGuardar: (valor: string) => void;
  type?: "text" | "date";
}) {
  const [valor, setValor] = useState(valorInicial);

  useEffect(() => {
    setValor(valorInicial);
  }, [valorInicial]);

  return (
    <Input
      type={type}
      value={valor}
      onClick={(evento) => evento.stopPropagation()}
      onChange={(evento) => setValor(evento.target.value)}
      onBlur={() => {
        if (valor.trim() !== "" && valor !== valorInicial) onGuardar(valor);
      }}
    />
  );
}

// --- Notas colaborativas (expandible por fila) ---------------------------------------

function PanelNotas({ accionId }: { accionId: string }) {
  const queryClient = useQueryClient();
  const [texto, setTexto] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["notas-seguimiento", accionId],
    queryFn: () => listarNotasDeAccion(accionId),
  });

  const agregarMutacion = useMutation({
    mutationFn: (texto: string) => agregarNotaAAccion(accionId, texto),
    onSuccess: () => {
      setTexto("");
      void queryClient.invalidateQueries({ queryKey: ["notas-seguimiento", accionId] });
    },
  });

  return (
    <div
      className="flex flex-col gap-3 rounded-md bg-secondary/40 p-4"
      onClick={(evento) => evento.stopPropagation()}
    >
      {isLoading && <p className="text-xs text-atenuado">Cargando notas...</p>}
      {data && data.length === 0 && <p className="text-xs text-muted-foreground">Todavía no hay notas.</p>}
      {data?.map((nota) => (
        <div key={nota.id} className="flex gap-2.5">
          <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-[0.65rem] font-bold text-primary-foreground">
            {nota.usuario_nombre.slice(0, 1).toUpperCase()}
          </span>
          <div>
            <p className="text-xs">
              <span className="font-semibold">{nota.usuario_nombre}</span>{" "}
              <span className="text-atenuado">· {new Date(nota.creado_en).toLocaleDateString("es")}</span>
            </p>
            <p className="text-sm">{nota.texto}</p>
          </div>
        </div>
      ))}
      <form
        className="flex gap-2"
        onSubmit={(evento) => {
          evento.preventDefault();
          if (texto.trim() === "") return;
          agregarMutacion.mutate(texto.trim());
        }}
      >
        <Input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Agregar una nota..."
          className="bg-background"
        />
        <Button type="submit" size="sm" disabled={agregarMutacion.isPending || texto.trim() === ""}>
          Agregar
        </Button>
      </form>
    </div>
  );
}

function FilaAccion({
  accion,
  expandido,
  onToggleExpandir,
  onActualizar,
}: {
  accion: AccionSeguimientoResponse;
  expandido: boolean;
  onToggleExpandir: () => void;
  onActualizar: (accionId: string, cambios: ActualizarAccionSeguimientoPayload) => void;
}) {
  const navigate = useNavigate();

  return (
    <>
      <tr
        className="cursor-pointer border-b border-border last:border-0 hover:bg-secondary/50"
        onClick={() => void navigate(`/tramites/${accion.tramite_id}/plan`)}
      >
        <td className="py-3 pr-4 align-top">
          <p className="font-medium">{accion.descripcion}</p>
          <p className="text-xs text-muted-foreground">{accion.tramite_nombre}</p>
        </td>
        <td className="py-3 pr-4 align-top">
          <CampoTextoInline
            valorInicial={accion.responsable}
            onGuardar={(responsable) => onActualizar(accion.id, { responsable })}
          />
        </td>
        <td className="py-3 pr-4 align-top">
          <CampoTextoInline
            type="date"
            valorInicial={accion.fecha_objetivo}
            onGuardar={(fecha_objetivo) => onActualizar(accion.id, { fecha_objetivo })}
          />
        </td>
        <td className="py-3 pr-4 align-top">
          <div className="flex flex-col items-start gap-2">
            <BadgeSemaforo estado={accion.estado_semaforo} />
            <SelectorSemaforo
              valor={accion.estado_semaforo}
              onCambiar={(estado_semaforo) => onActualizar(accion.id, { estado_semaforo })}
            />
          </div>
        </td>
        <td className="py-3 pr-0 align-top text-right">
          <button
            type="button"
            onClick={(evento) => {
              evento.stopPropagation();
              onToggleExpandir();
            }}
            className="text-sm font-medium text-primary underline-offset-2 hover:underline"
          >
            Notas {expandido ? "▲" : "▼"}
          </button>
        </td>
      </tr>
      {expandido && (
        <tr className="border-b border-border last:border-0">
          <td colSpan={5} className="pb-4">
            <PanelNotas accionId={accion.id} />
          </td>
        </tr>
      )}
    </>
  );
}

export function Seguimiento() {
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["seguimiento"],
    queryFn: listarAccionesSeguimiento,
  });

  const mutacion = useMutation({
    mutationFn: ({ accionId, cambios }: { accionId: string; cambios: ActualizarAccionSeguimientoPayload }) =>
      actualizarAccionSeguimiento(accionId, cambios),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["seguimiento"] }),
  });

  const actualizar = (accionId: string, cambios: ActualizarAccionSeguimientoPayload) => {
    mutacion.mutate({ accionId, cambios });
  };

  const [expandidoId, setExpandidoId] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState("");
  const [filtroEstado, setFiltroEstado] = useState<EstadoSemaforo | typeof TODOS>(TODOS);
  const [filtroResponsable, setFiltroResponsable] = useState(TODOS);

  const responsables = useMemo(
    () => [...new Set((data ?? []).map((a) => a.responsable))].sort((a, b) => a.localeCompare(b)),
    [data],
  );

  const datosFiltrados = useMemo(() => {
    if (!data) return undefined;
    const busquedaNormalizada = busqueda.trim().toLowerCase();
    return data.filter((accion) => {
      if (filtroEstado !== TODOS && accion.estado_semaforo !== filtroEstado) return false;
      if (filtroResponsable !== TODOS && accion.responsable !== filtroResponsable) return false;
      if (
        busquedaNormalizada &&
        !accion.descripcion.toLowerCase().includes(busquedaNormalizada) &&
        !accion.tramite_nombre.toLowerCase().includes(busquedaNormalizada)
      ) {
        return false;
      }
      return true;
    });
  }, [data, busqueda, filtroEstado, filtroResponsable]);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4 p-6">
      <div className="flex flex-wrap items-center gap-3">
        <Input
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder="Buscar acción o trámite..."
          className="max-w-64"
        />
        <select
          value={filtroEstado}
          onChange={(e) => setFiltroEstado(e.target.value as EstadoSemaforo | typeof TODOS)}
          className="min-h-[44px] rounded-md border border-input bg-background px-2 text-sm text-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          <option value={TODOS}>Estado: todos</option>
          {ORDEN_ESTADOS_SEMAFORO.map((estado) => (
            <option key={estado} value={estado}>
              {ESTADOS_SEMAFORO[estado].etiqueta}
            </option>
          ))}
        </select>
        <select
          value={filtroResponsable}
          onChange={(e) => setFiltroResponsable(e.target.value)}
          className="min-h-[44px] rounded-md border border-input bg-background px-2 text-sm text-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          <option value={TODOS}>Responsable: todos</option>
          {responsables.map((responsable) => (
            <option key={responsable} value={responsable}>
              {responsable}
            </option>
          ))}
        </select>
        {data && (
          <span className="ml-auto text-xs text-muted-foreground">
            {datosFiltrados?.length ?? 0} de {data.length} acciones
          </span>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Seguimiento de acciones</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <p className="text-sm text-atenuado">Cargando...</p>}
          {isError && <p className="text-sm text-destructive">No se pudo cargar el panel de seguimiento.</p>}
          {data && data.length === 0 && (
            <p className="text-sm text-muted-foreground">Todavía no hay ninguna acción de seguimiento.</p>
          )}
          {data && data.length > 0 && datosFiltrados && datosFiltrados.length === 0 && (
            <p className="text-sm text-muted-foreground">Ninguna acción coincide con los filtros.</p>
          )}
          {datosFiltrados && datosFiltrados.length > 0 && (
            // overflow-x-auto propio -- ver misma nota en AdminSaludIA.tsx.
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-muted-foreground">
                    <th className="py-2 pr-4 font-medium">Acción</th>
                    <th className="py-2 pr-4 font-medium">Responsable</th>
                    <th className="py-2 pr-4 font-medium">Fecha objetivo</th>
                    <th className="py-2 pr-4 font-medium">Estado</th>
                    <th className="py-2 font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {datosFiltrados.map((accion) => (
                    <FilaAccion
                      key={accion.id}
                      accion={accion}
                      expandido={expandidoId === accion.id}
                      onToggleExpandir={() => setExpandidoId((actual) => (actual === accion.id ? null : accion.id))}
                      onActualizar={actualizar}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

import { useEffect, useState } from "react";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ESTADOS_SEMAFORO, ORDEN_ESTADOS_SEMAFORO, type EstadoSemaforo } from "@/lib/semaforo";
import {
  actualizarAccionSeguimiento,
  listarAccionesSeguimiento,
  type AccionSeguimientoResponse,
  type ActualizarAccionSeguimientoPayload,
} from "@/lib/seguimientoApi";

// Panel de seguimiento (docs/ux-brief.md sección "5. Panel de seguimiento",
// docs/app-flow.md paso 5): tabla simple de todas las acciones de todos los
// trámites con plan generado, con edición inline de responsable/fecha objetivo/
// semáforo directamente en la fila -- sin Gantt, sin dependencias entre tareas,
// sin ningún campo adicional a los 4 ya definidos (mandato explícito de "nada de
// metodologías pesadas"). Clic en la fila navega al plan del trámite de esa
// acción; los controles de edición detienen la propagación del clic.

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

function FilaAccion({
  accion,
  onActualizar,
}: {
  accion: AccionSeguimientoResponse;
  onActualizar: (accionId: string, cambios: ActualizarAccionSeguimientoPayload) => void;
}) {
  const navigate = useNavigate();

  return (
    <tr
      className="cursor-pointer border-b border-border last:border-0 hover:bg-secondary/50"
      onClick={() => navigate(`/tramites/${accion.tramite_id}/plan`)}
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
      <td className="py-3 pr-0 align-top">
        <div className="flex flex-col items-start gap-2">
          <BadgeSemaforo estado={accion.estado_semaforo} />
          <SelectorSemaforo
            valor={accion.estado_semaforo}
            onCambiar={(estado_semaforo) => onActualizar(accion.id, { estado_semaforo })}
          />
        </div>
      </td>
    </tr>
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

  return (
    <div className="mx-auto max-w-4xl p-6">
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
          {data && data.length > 0 && (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th className="py-2 pr-4 font-medium">Acción</th>
                  <th className="py-2 pr-4 font-medium">Responsable</th>
                  <th className="py-2 pr-4 font-medium">Fecha objetivo</th>
                  <th className="py-2 font-medium">Estado</th>
                </tr>
              </thead>
              <tbody>
                {data.map((accion) => (
                  <FilaAccion key={accion.id} accion={accion} onActualizar={actualizar} />
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

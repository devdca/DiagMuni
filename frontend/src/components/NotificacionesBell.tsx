import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import {
  listarNotificaciones,
  marcarNotificacionLeida,
  marcarTodasLeidas,
  type NotificacionResponse,
} from "@/lib/notificacionesApi";

// Centro de notificaciones (campana de la barra superior) -- vive en NavBar.tsx,
// visible en cualquier pantalla con sesión. Sondeo cada 30s (sin WebSocket: el
// resto del proyecto ya evita infraestructura nueva cuando no hace falta, ver
// docs/TRD.md "Observabilidad").
const INTERVALO_SONDEO_MS = 30_000;

function formatearRelativo(fechaIso: string): string {
  const ahora = Date.now();
  const fecha = new Date(fechaIso).getTime();
  const minutos = Math.round((ahora - fecha) / 60_000);
  if (minutos < 1) return "justo ahora";
  if (minutos < 60) return `hace ${minutos} min`;
  const horas = Math.round(minutos / 60);
  if (horas < 24) return `hace ${horas} h`;
  const dias = Math.round(horas / 24);
  return `hace ${dias} d`;
}

function IconoCampana() {
  return (
    <svg aria-hidden viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-[18px]">
      <path d="M10 3a4 4 0 0 0-4 4v2.2c0 .5-.15 1-.44 1.4L4.3 12.6c-.5.7 0 1.7.85 1.7h9.7c.85 0 1.35-1 .85-1.7l-1.26-2c-.29-.4-.44-.9-.44-1.4V7a4 4 0 0 0-4-4Z" />
      <path d="M8.3 16a1.8 1.8 0 0 0 3.4 0" />
    </svg>
  );
}

function FilaNotificacion({
  notificacion,
  onClic,
}: {
  notificacion: NotificacionResponse;
  onClic: (n: NotificacionResponse) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onClic(notificacion)}
      className={`flex w-full flex-col gap-0.5 rounded-md px-3 py-2 text-left transition-colors hover:bg-secondary/70 ${
        notificacion.leida ? "" : "bg-primary/5"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-medium">{notificacion.titulo}</span>
        {!notificacion.leida && <span aria-hidden className="mt-1 size-2 shrink-0 rounded-full bg-primary" />}
      </div>
      <p className="text-xs text-muted-foreground">{notificacion.mensaje}</p>
      <span className="text-[0.68rem] text-atenuado">{formatearRelativo(notificacion.creado_en)}</span>
    </button>
  );
}

export function NotificacionesBell() {
  const [abierto, setAbierto] = useState(false);
  const contenedorRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data } = useQuery({
    queryKey: ["notificaciones"],
    queryFn: listarNotificaciones,
    refetchInterval: INTERVALO_SONDEO_MS,
  });

  useEffect(() => {
    function alClicFuera(evento: MouseEvent) {
      if (contenedorRef.current && !contenedorRef.current.contains(evento.target as Node)) {
        setAbierto(false);
      }
    }
    document.addEventListener("mousedown", alClicFuera);
    return () => document.removeEventListener("mousedown", alClicFuera);
  }, []);

  const leerMutacion = useMutation({
    mutationFn: marcarNotificacionLeida,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["notificaciones"] }),
  });

  const leerTodasMutacion = useMutation({
    mutationFn: marcarTodasLeidas,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["notificaciones"] }),
  });

  function alClicNotificacion(notificacion: NotificacionResponse) {
    if (!notificacion.leida) leerMutacion.mutate(notificacion.id);
    if (notificacion.tramite_id) {
      setAbierto(false);
      void navigate(`/tramites/${notificacion.tramite_id}/plan`);
    }
  }

  const noLeidas = data?.no_leidas ?? 0;

  return (
    <div ref={contenedorRef} className="relative">
      <button
        type="button"
        aria-label="Notificaciones"
        onClick={() => setAbierto((actual) => !actual)}
        className="relative flex size-10 items-center justify-center rounded-md border border-border bg-background text-foreground transition-colors hover:bg-secondary"
      >
        <IconoCampana />
        {noLeidas > 0 && (
          <span className="absolute -top-1 -right-1 flex min-w-[18px] items-center justify-center rounded-full bg-destructive px-1 text-[0.65rem] font-bold text-destructive-foreground">
            {noLeidas > 9 ? "9+" : noLeidas}
          </span>
        )}
      </button>

      {abierto && (
        <div className="absolute top-full right-0 z-50 mt-2 flex max-h-[70vh] w-80 flex-col overflow-hidden rounded-lg border border-border bg-card shadow-lg">
          <div className="flex items-center justify-between border-b border-border px-3 py-2">
            <span className="text-sm font-semibold">Notificaciones</span>
            {noLeidas > 0 && (
              <button
                type="button"
                onClick={() => leerTodasMutacion.mutate()}
                className="text-xs font-medium text-primary"
              >
                Marcar todas como leídas
              </button>
            )}
          </div>
          <div className="flex flex-col gap-0.5 overflow-y-auto p-1.5">
            {!data || data.notificaciones.length === 0 ? (
              <p className="p-3 text-sm text-muted-foreground">No tienes notificaciones.</p>
            ) : (
              data.notificaciones.map((n) => <FilaNotificacion key={n.id} notificacion={n} onClic={alClicNotificacion} />)
            )}
          </div>
        </div>
      )}
    </div>
  );
}

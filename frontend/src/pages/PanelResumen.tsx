import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { obtenerNivelMadurez } from "@/lib/madurez";

import { obtenerPanelResumen, type TramiteResponse } from "../lib/tramitesApi";

// Panel resumen (docs/ux-brief.md, "2. Panel resumen"): tarjeta con el índice de
// madurez global y fecha de último diagnóstico, más la tabla de trámites
// catalogados con su índice individual y acceso a la acción que corresponda
// según su estado. Sin gráficas de tendencia (mandato explícito del documento).

function formatearFecha(fechaIso: string): string {
  return new Date(fechaIso).toLocaleDateString("es", { year: "numeric", month: "long", day: "numeric" });
}

function BadgeIndice({ indice }: { indice: number | null }) {
  if (indice === null) {
    return <Badge variant="outline">Sin diagnosticar</Badge>;
  }
  const nivel = obtenerNivelMadurez(indice);
  return (
    <Badge variant="outline" style={{ borderColor: nivel.hexClaro, color: nivel.hexClaro }}>
      <span aria-hidden className="inline-block size-2 rounded-full" style={{ backgroundColor: nivel.hexClaro }} />
      {nivel.nivel} — {nivel.etiqueta}
    </Badge>
  );
}

function AccionTramite({ tramite }: { tramite: TramiteResponse }) {
  const navigate = useNavigate();

  if (tramite.estado === "sin_iniciar" || tramite.estado === "en_progreso") {
    return (
      <Button size="sm" onClick={() => navigate(`/tramites/${tramite.id}/diagnostico`)}>
        Continuar diagnóstico
      </Button>
    );
  }

  if (tramite.estado === "plan_listo") {
    return (
      <Button size="sm" onClick={() => navigate(`/tramites/${tramite.id}/plan`)}>
        Ver plan
      </Button>
    );
  }

  // "diagnosticado" / "generando_plan": enviar_diagnostico (backend/app/api/
  // diagnosticos.py) ya dispara el job de generación del plan automáticamente,
  // sin ninguna acción manual pendiente del funcionario -- decisión de esta
  // tarea (docs/ux-brief.md no fija este caso): mostrar un texto de espera en
  // vez de un botón de acción, para no sugerir que hay algo que hacer.
  return <span className="text-sm text-atenuado">Generando plan de modernización...</span>;
}

export function PanelResumen() {
  const { data, isLoading, isError } = useQuery({ queryKey: ["panel-resumen"], queryFn: obtenerPanelResumen });

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle>Índice de madurez global</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <p className="text-sm text-atenuado">Cargando...</p>}
          {isError && <p className="text-sm text-destructive">No se pudo cargar el panel resumen.</p>}
          {data && (
            <>
              <div className="flex items-end gap-3">
                {data.indice_global === null ? (
                  <p className="text-lg">Todavía no hay ningún trámite diagnosticado.</p>
                ) : (
                  <>
                    <span
                      className="text-5xl font-semibold tabular-nums"
                      style={{ color: obtenerNivelMadurez(data.indice_global).hexClaro }}
                    >
                      {data.indice_global.toFixed(1)}
                    </span>
                    <span className="pb-1 text-lg">{obtenerNivelMadurez(data.indice_global).etiqueta}</span>
                  </>
                )}
              </div>
              <p className="mt-2 text-sm text-muted-foreground">
                {data.fecha_ultimo_diagnostico
                  ? `Último diagnóstico: ${formatearFecha(data.fecha_ultimo_diagnostico)}`
                  : "Aún no hay ningún diagnóstico completado."}
              </p>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Trámites catalogados</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-muted-foreground">
                <th className="py-2 font-medium">Trámite</th>
                <th className="py-2 font-medium">Índice</th>
                <th className="py-2 pr-0 text-right font-medium">Acción</th>
              </tr>
            </thead>
            <tbody>
              {data?.tramites.map((tramite) => (
                <tr key={tramite.id} className="border-b border-border last:border-0">
                  <td className="py-3 pr-4">{tramite.nombre}</td>
                  <td className="py-3 pr-4">
                    <BadgeIndice indice={tramite.indice_madurez} />
                  </td>
                  <td className="py-3 text-right">
                    <AccionTramite tramite={tramite} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}

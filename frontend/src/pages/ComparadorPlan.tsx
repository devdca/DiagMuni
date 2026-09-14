import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  obtenerVersionPlan,
  obtenerVersionesPlan,
  type Brecha,
  type PlanVersionDetalle,
  type VersionPlanResumen,
} from "@/lib/planApi";

// Comparador de versiones del plan (/tramites/:tramiteId/plan/comparar) -- deja
// ver qué cambió entre dos versiones cualesquiera del mismo trámite (nunca se
// borran, docs/backend-schema.md). Reachable desde Plan.tsx ("Comparar
// versiones", solo si hay más de una versión).

function etiquetaVersion(v: VersionPlanResumen): string {
  const fecha = new Date(v.generado_en).toLocaleDateString("es", { year: "numeric", month: "short", day: "numeric" });
  return `Versión ${v.version} · ${fecha}`;
}

function SelectorVersion({
  etiqueta,
  versiones,
  valor,
  onCambiar,
}: {
  etiqueta: string;
  versiones: VersionPlanResumen[];
  valor: number | null;
  onCambiar: (version: number) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-muted-foreground">{etiqueta}</label>
      <select
        value={valor ?? ""}
        onChange={(e) => onCambiar(Number(e.target.value))}
        className="min-h-[44px] rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        {versiones.map((v) => (
          <option key={v.version} value={v.version}>
            {etiquetaVersion(v)}
          </option>
        ))}
      </select>
    </div>
  );
}

function TarjetaBrechaResumen({ brecha, estado }: { brecha: Brecha; estado: "resuelta" | "nueva" | "persistente" }) {
  const estilos = {
    resuelta: { badge: "Resuelta ✓", clase: "border-l-4 border-l-emerald-500" },
    nueva: { badge: "Nueva", clase: "border-l-4 border-l-primary" },
    persistente: { badge: "Sin cambios", clase: "" },
  }[estado];

  return (
    <div className={`rounded-md border border-border p-3 ${estilos.clase}`}>
      <div className="mb-1 flex items-center gap-2">
        <Badge variant="outline">{estilos.badge}</Badge>
        <span className="font-medium">{brecha.variable}</span>
      </div>
      <p className="text-sm text-muted-foreground">{brecha.narrativa}</p>
    </div>
  );
}

export function ComparadorPlan() {
  const { tramiteId } = useParams<{ tramiteId: string }>();
  const navigate = useNavigate();

  const versionesQuery = useQuery({
    queryKey: ["plan-versiones", tramiteId],
    queryFn: () => obtenerVersionesPlan(tramiteId!),
    enabled: !!tramiteId,
  });

  const [versionA, setVersionA] = useState<number | null>(null);
  const [versionB, setVersionB] = useState<number | null>(null);

  // Default: la más reciente vs. la inmediatamente anterior -- el caso de uso más
  // común ("¿qué cambió con la última corrección?"). Solo corre una vez, cuando
  // llegan las versiones por primera vez.
  useEffect(() => {
    const versiones = versionesQuery.data;
    if (!versiones || versiones.length === 0 || versionB !== null) return;
    setVersionB(versiones[0].version);
    setVersionA(versiones.length > 1 ? versiones[1].version : versiones[0].version);
  }, [versionesQuery.data, versionB]);

  const detalleAQuery = useQuery({
    queryKey: ["plan-version-detalle", tramiteId, versionA],
    queryFn: () => obtenerVersionPlan(tramiteId!, versionA!),
    enabled: !!tramiteId && versionA !== null,
  });
  const detalleBQuery = useQuery({
    queryKey: ["plan-version-detalle", tramiteId, versionB],
    queryFn: () => obtenerVersionPlan(tramiteId!, versionB!),
    enabled: !!tramiteId && versionB !== null,
  });

  if (!tramiteId) return null;

  if (versionesQuery.isLoading) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-sm text-atenuado">Cargando...</p>
      </div>
    );
  }

  if (versionesQuery.isError || !versionesQuery.data) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-sm text-destructive">No se pudo cargar el historial de versiones del plan.</p>
      </div>
    );
  }

  const versiones = versionesQuery.data;
  const detalleA: PlanVersionDetalle | undefined = detalleAQuery.data;
  const detalleB: PlanVersionDetalle | undefined = detalleBQuery.data;

  let diferencia: { resueltas: Brecha[]; nuevas: Brecha[]; persistentes: Brecha[] } | null = null;
  if (detalleA && detalleB) {
    const mapaA = new Map(detalleA.contenido.brechas.map((b) => [b.variable, b]));
    const mapaB = new Map(detalleB.contenido.brechas.map((b) => [b.variable, b]));
    diferencia = {
      resueltas: [...mapaA.values()].filter((b) => !mapaB.has(b.variable)),
      nuevas: [...mapaB.values()].filter((b) => !mapaA.has(b.variable)),
      persistentes: [...mapaB.values()].filter((b) => mapaA.has(b.variable)),
    };
  }

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 p-6">
      <div className="flex flex-col gap-2">
        <button
          type="button"
          onClick={() => void navigate(`/tramites/${tramiteId}/plan`)}
          className="w-fit text-xs text-muted-foreground underline underline-offset-2"
        >
          ← Volver al plan
        </button>
        <h2 className="text-lg font-semibold">Comparar versiones del plan</h2>
      </div>

      <Card>
        <CardContent className="flex flex-wrap gap-4 pt-6">
          <SelectorVersion etiqueta="Versión anterior" versiones={versiones} valor={versionA} onCambiar={setVersionA} />
          <SelectorVersion etiqueta="Versión actual" versiones={versiones} valor={versionB} onCambiar={setVersionB} />
        </CardContent>
      </Card>

      {(detalleAQuery.isLoading || detalleBQuery.isLoading) && <p className="text-sm text-atenuado">Cargando...</p>}

      {diferencia && (
        <>
          <Card>
            <CardContent className="flex flex-wrap gap-8 pt-6">
              <div>
                <div className="text-xs text-muted-foreground">Brechas resueltas</div>
                <div className="text-2xl font-semibold text-emerald-600 dark:text-emerald-400 tabular-nums">
                  {diferencia.resueltas.length}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Brechas nuevas</div>
                <div className="text-2xl font-semibold text-primary tabular-nums">{diferencia.nuevas.length}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Sin cambios</div>
                <div className="text-2xl font-semibold tabular-nums">{diferencia.persistentes.length}</div>
              </div>
            </CardContent>
          </Card>

          {diferencia.resueltas.length === 0 && diferencia.nuevas.length === 0 && (
            <p className="text-sm text-muted-foreground">No hay diferencias en las brechas entre estas dos versiones.</p>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Detalle</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {diferencia.resueltas.map((b) => (
                <TarjetaBrechaResumen key={`resuelta-${b.variable}`} brecha={b} estado="resuelta" />
              ))}
              {diferencia.nuevas.map((b) => (
                <TarjetaBrechaResumen key={`nueva-${b.variable}`} brecha={b} estado="nueva" />
              ))}
              {diferencia.persistentes.map((b) => (
                <TarjetaBrechaResumen key={`persistente-${b.variable}`} brecha={b} estado="persistente" />
              ))}
            </CardContent>
          </Card>
        </>
      )}

      <Button variant="outline" onClick={() => void navigate(`/tramites/${tramiteId}/plan`)}>
        Volver al plan
      </Button>
    </div>
  );
}

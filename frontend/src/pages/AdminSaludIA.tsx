import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { AdminTabs } from "@/components/AdminTabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  actualizarProveedorLlm,
  obtenerResumenSaludIa,
  type ActualizarProveedorLlmPayload,
  type PlanRecienteResponse,
  type ProveedorLlm,
  type ResumenSaludIaResponse,
} from "@/lib/saludIaApi";

// "Salud del sistema" (solo admin_gobierno): estado del proveedor de IA y
// actividad reciente, sin ningún stack de observabilidad nuevo.

function etiquetaProveedor(proveedor: string | null): string {
  if (proveedor === null) return "Ninguno (modo degradado)";
  const etiquetas: Record<string, string> = { deepseek: "DeepSeek", anthropic: "Anthropic (Claude)", local: "Local (Ollama)" };
  return etiquetas[proveedor] ?? proveedor;
}

function formatearFecha(fechaIso: string): string {
  return new Date(fechaIso).toLocaleString("es", { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function BadgeModo({ modo }: { modo: "llm" | "degradado" }) {
  return modo === "llm" ? (
    <Badge variant="outline">LLM</Badge>
  ) : (
    <Badge variant="secondary">Degradado</Badge>
  );
}

function FilaPlan({ plan }: { plan: PlanRecienteResponse }) {
  return (
    <tr className="border-b border-border last:border-0">
      <td className="py-2 pr-4 font-medium">{plan.tramite_nombre}</td>
      <td className="py-2 pr-4 text-muted-foreground">{plan.version}</td>
      <td className="py-2 pr-4">
        <BadgeModo modo={plan.modo} />
      </td>
      <td className="py-2 pr-4">{plan.verificado ? <Badge variant="outline">Verificado</Badge> : <Badge variant="secondary">Sin verificar</Badge>}</td>
      <td className="py-2 text-muted-foreground">{formatearFecha(plan.generado_en)}</td>
    </tr>
  );
}

// BYOK: la preferencia de proveedor se guarda al elegirla; la credencial usa
// un botón "Guardar" explícito -- no dispara una mutación por cada tecla.
function ConfiguracionProveedorIa({ data }: { data: ResumenSaludIaResponse }) {
  const queryClient = useQueryClient();
  const [credencial, setCredencial] = useState("");

  const guardar = useMutation({
    mutationFn: (cambios: ActualizarProveedorLlmPayload) => actualizarProveedorLlm(cambios),
    onSuccess: (respuesta) => {
      queryClient.setQueryData(["admin-salud-ia"], respuesta);
      setCredencial("");
    },
  });

  const proveedor = data.proveedor_preferido;
  const yaConfigurada =
    proveedor === "anthropic"
      ? data.anthropic_key_configurada
      : proveedor === "deepseek"
        ? data.deepseek_key_configurada
        : false;

  function guardarCredencial() {
    if (proveedor === "anthropic") guardar.mutate({ anthropic_api_key: credencial });
    else if (proveedor === "deepseek") guardar.mutate({ deepseek_api_key: credencial });
    else if (proveedor === "local") guardar.mutate({ ollama_api_base: credencial });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Proveedor de IA</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm text-muted-foreground">
          Tu gobierno paga y controla su propia API key -- DiagMuni nunca la muestra de nuevo una vez guardada.
        </p>

        <div className="flex flex-col gap-1">
          <label htmlFor="proveedor-llm" className="text-sm font-medium">
            Proveedor preferido
          </label>
          <select
            id="proveedor-llm"
            value={proveedor ?? ""}
            disabled={guardar.isPending}
            onChange={(e) => guardar.mutate({ proveedor: (e.target.value || null) as ProveedorLlm | null })}
            className="min-h-11 w-fit max-w-64 rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
          >
            <option value="">Automático (configuración global)</option>
            {data.proveedores_disponibles.map((p) => (
              <option key={p} value={p}>
                {etiquetaProveedor(p)}
              </option>
            ))}
          </select>
        </div>

        {proveedor && (
          <div className="flex flex-col gap-1">
            <label htmlFor="credencial-llm" className="text-sm font-medium">
              {proveedor === "local" ? "URL de tu servidor Ollama" : `Tu API key de ${etiquetaProveedor(proveedor)}`}
            </label>
            <div className="flex flex-wrap gap-2">
              <Input
                id="credencial-llm"
                type={proveedor === "local" ? "text" : "password"}
                value={credencial}
                onChange={(e) => setCredencial(e.target.value)}
                placeholder={yaConfigurada ? "•••• configurada" : "Sin configurar"}
                className="max-w-80"
              />
              <Button
                type="button"
                variant="outline"
                disabled={!credencial.trim() || guardar.isPending}
                onClick={guardarCredencial}
              >
                {guardar.isPending ? "Guardando..." : "Guardar"}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function AdminSaludIA() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["admin-salud-ia"],
    queryFn: obtenerResumenSaludIa,
  });

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 p-6">
      <div>
        <h2 className="text-lg font-semibold">Administración del gobierno</h2>
        <p className="text-sm text-muted-foreground">
          Estado del sistema de generación de planes -- solo visible para el rol Administrador.
        </p>
      </div>

      <AdminTabs activa="salud-ia" />

      {isLoading && <p className="text-sm text-atenuado">Cargando...</p>}
      {isError && <p className="text-sm text-destructive">No se pudo cargar el estado del sistema.</p>}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Card>
              <CardContent className="flex flex-col gap-1 pt-6">
                <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Proveedor activo</span>
                <span className="text-xl font-semibold">{etiquetaProveedor(data.proveedor_activo)}</span>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex flex-col gap-1 pt-6">
                <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Último plan generado</span>
                <span className="text-xl font-semibold">
                  {data.ultimo_plan ? formatearFecha(data.ultimo_plan.generado_en) : "Ninguno todavía"}
                </span>
                {data.ultimo_plan && (
                  <span className="text-xs text-muted-foreground">
                    {data.ultimo_plan.tramite_nombre} · versión {data.ultimo_plan.version}
                  </span>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex flex-col gap-1 pt-6">
                <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                  Jobs fallidos (24h)
                </span>
                <span
                  className={`text-xl font-semibold ${data.jobs_fallidos_24h > 0 ? "text-destructive" : ""}`}
                >
                  {data.jobs_fallidos_24h}
                </span>
              </CardContent>
            </Card>
          </div>

          <ConfiguracionProveedorIa data={data} />

          <Card>
            <CardHeader>
              <CardTitle>Planes generados recientemente</CardTitle>
            </CardHeader>
            <CardContent>
              {data.planes_recientes.length === 0 ? (
                <p className="text-sm text-muted-foreground">Todavía no se ha generado ningún plan.</p>
              ) : (
                // Scroll horizontal propio: si la ventana se achica, solo la tabla
                // se desplaza, no toda la página.
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-border text-muted-foreground">
                        <th className="py-2 pr-4 font-medium">Trámite</th>
                        <th className="py-2 pr-4 font-medium">Versión</th>
                        <th className="py-2 pr-4 font-medium">Modo</th>
                        <th className="py-2 pr-4 font-medium">Estado</th>
                        <th className="py-2 font-medium">Generado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.planes_recientes.map((plan, i) => (
                        <FilaPlan key={`${plan.tramite_id}-${plan.version}-${i}`} plan={plan} />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

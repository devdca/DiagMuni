import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { obtenerNivelMadurez } from "@/lib/madurez";

import {
  archivarTramite,
  crearTramite,
  desarchivarTramite,
  eliminarTramite,
  obtenerPanelResumen,
  type TramiteResponse,
} from "../lib/tramitesApi";

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

  // "diagnosticado" / "generando_plan": enviar_diagnostico (backend/app/api/
  // diagnosticos.py) ya dispara el job de generación del plan automáticamente,
  // sin ninguna acción manual pendiente del funcionario -- decisión de esta
  // tarea (docs/ux-brief.md no fija este caso): mostrar un texto de espera en
  // vez de un botón de acción, para no sugerir que hay algo que hacer.
  return <span className="text-sm text-atenuado">Generando plan de modernización...</span>;
}

// Gestión de un trámite: eliminar (borrado físico, backend/app/api/tramites.py
// solo lo permite si `completado_en` es null -- mismo campo que ya trae
// TramiteResponse, sin duplicar esa regla en el frontend) o archivar/desarchivar
// (reversible, oculta del panel sin borrar nada). `window.confirm` en vez de un
// modal propio -- no existe un componente de diálogo en el kit de UI todavía y el
// resto de este panel ya sigue el criterio de "sin metodologías pesadas"
// (docs/ux-brief.md) para lo que no lo necesita.
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
        <Button
          size="sm"
          variant="outline"
          disabled={eliminarMutacion.isPending}
          onClick={() => {
            if (window.confirm(`¿Eliminar el trámite "${tramite.nombre}"? Esta acción no se puede deshacer.`)) {
              eliminarMutacion.mutate(tramite.id);
            }
          }}
        >
          Eliminar
        </Button>
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

// Alta de un trámite en el catálogo (docs/app-flow.md, "Estados del trámite":
// `sin_iniciar` lo origina la "Alta del trámite en el catálogo") -- ese documento
// nunca fijó en qué pantalla ocurre; POST /api/tramites (backend/app/api/
// tramites.py) ya existía sin ningún formulario que lo llamara. Formulario simple
// (nombre obligatorio, descripción opcional), sin modal -- mismo criterio de "sin
// metodologías pesadas" que el resto del panel.
function FormularioNuevoTramite({ abierto, onCerrar }: { abierto: boolean; onCerrar: () => void }) {
  const queryClient = useQueryClient();
  const [nombre, setNombre] = useState("");
  const [descripcion, setDescripcion] = useState("");

  const crearMutacion = useMutation({
    mutationFn: crearTramite,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["panel-resumen"] });
      setNombre("");
      setDescripcion("");
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
        crearMutacion.mutate({ nombre: nombre.trim(), descripcion: descripcion.trim() });
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
          required
        />
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

export function PanelResumen() {
  const [verArchivados, setVerArchivados] = useState(false);
  // El query key incluye `verArchivados` -- son dos listas mutuamente excluyentes
  // (backend/app/api/tramites.py nunca las mezcla), no una misma lista filtrada
  // en el cliente.
  const { data, isLoading, isError } = useQuery({
    queryKey: ["panel-resumen", verArchivados],
    queryFn: () => obtenerPanelResumen(verArchivados),
  });
  const [formularioAbierto, setFormularioAbierto] = useState(false);

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
            <FormularioNuevoTramite abierto={formularioAbierto} onCerrar={() => setFormularioAbierto(false)} />
          )}
          {verArchivados && data?.tramites.length === 0 && (
            <p className="text-sm text-atenuado">No hay ningún trámite archivado.</p>
          )}
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-muted-foreground">
                <th className="py-2 font-medium">Trámite</th>
                <th className="py-2 font-medium">Índice</th>
                {!verArchivados && <th className="py-2 font-medium">Acción</th>}
                <th className="py-2 pr-0 text-right font-medium">Gestión</th>
              </tr>
            </thead>
            <tbody>
              {data?.tramites.map((tramite) => (
                <tr key={tramite.id} className="border-b border-border last:border-0">
                  <td className="py-3 pr-4">{tramite.nombre}</td>
                  <td className="py-3 pr-4">
                    <BadgeIndice indice={tramite.indice_madurez} />
                  </td>
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
        </CardContent>
      </Card>
    </div>
  );
}

import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError } from "@/lib/httpClient";
import { obtenerNivelMadurez } from "@/lib/madurez";
import { obtenerPlan, type Brecha, type ComponenteRecomendado, type CostoComponente } from "@/lib/planApi";

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

function EncabezadoIndice({ actual, sinBrechas }: { actual: number; sinBrechas: boolean }) {
  const nivelActual = obtenerNivelMadurez(actual);
  const nivelObjetivo = obtenerNivelMadurez(INDICE_OBJETIVO);

  return (
    <div className="flex items-center gap-4">
      <div className="flex flex-col items-center">
        <span className="text-4xl font-semibold tabular-nums" style={{ color: nivelActual.hexClaro }}>
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
            <span className="text-4xl font-semibold tabular-nums" style={{ color: nivelObjetivo.hexClaro }}>
              {nivelObjetivo.nivel}
            </span>
            <span className="text-xs text-muted-foreground">{nivelObjetivo.etiqueta}</span>
          </div>
        </>
      )}
    </div>
  );
}

export function Plan() {
  const { tramiteId } = useParams<{ tramiteId: string }>();
  const navigate = useNavigate();

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
              <Button onClick={() => navigate(`/tramites/${tramiteId}/diagnostico`)}>Ir al diagnóstico</Button>
              <Button variant="outline" onClick={() => navigate("/")}>
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
            <Button variant="outline" onClick={() => navigate("/")}>
              Volver al panel resumen
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const brechas = data.contenido.brechas;
  const sinBrechas = brechas.length === 0;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle>Plan de modernización</CardTitle>
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

      {!sinBrechas && (
        <Card>
          <CardHeader>
            <CardTitle>Detalle por brecha</CardTitle>
          </CardHeader>
          <CardContent>
            <Accordion type="multiple">
              {brechas.map((brecha, indice) => (
                <ItemBrecha key={`${brecha.variable}-${indice}`} brecha={brecha} indice={indice} />
              ))}
            </Accordion>
          </CardContent>
        </Card>
      )}

      <Button variant="outline" onClick={() => navigate("/seguimiento")}>
        Ir al seguimiento
      </Button>
    </div>
  );
}

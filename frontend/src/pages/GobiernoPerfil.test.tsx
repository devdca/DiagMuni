import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ContextoInstitucionalResponse } from "@/lib/gobiernoContextoApi";
import { GobiernoPerfil } from "./GobiernoPerfil";

// "Los campos discretos (RadioGroup, Select) guardan al elegir una opción"
// (comentario del propio archivo) -- este test cubre justo esa regla real de
// negocio: un RadioGroup booleano debe disparar el guardado apenas se elige,
// sin botón "Guardar" aparte, y el payload debe llevar solo ESE campo (upsert
// parcial), no los ~30 restantes.

vi.mock("@/lib/gobiernoContextoApi", async () => {
  const real = await vi.importActual<typeof import("@/lib/gobiernoContextoApi")>("@/lib/gobiernoContextoApi");
  return { ...real, obtenerContextoInstitucional: vi.fn(), guardarContextoInstitucional: vi.fn() };
});
vi.mock("@/lib/session", () => ({ obtenerPais: () => "mx", esAdmin: () => false }));

import { guardarContextoInstitucional, obtenerContextoInstitucional } from "@/lib/gobiernoContextoApi";

// Objeto "en blanco" -- ningún campo llenado todavía, mismo shape que el
// backend devuelve para un tenant recién creado (gobierno_contexto.py, GET
// nunca 404, sintetiza un shape vacío -- ver ese router).
const CONTEXTO_VACIO: ContextoInstitucionalResponse = {
  tenant_id: "11111111-1111-1111-1111-111111111111",
  poblacion_total: null,
  personal_total_gobierno: null,
  presupuesto_tic_anual: null,
  area_tic_existe: null,
  conectividad: null,
  normativa_local_emitida: null,
  autoridad_gobernanza_digital: null,
  agenda_simplificacion_publicada: null,
  portal_datos_abiertos_existe: null,
  linea_atencion_ciudadana_centralizada: null,
  capacitacion_personal_tic_anual: null,
  protocolo_ciberseguridad_existe: null,
  presupuesto_total_anual: null,
  numero_tramites_totales: null,
  ingresos_propios_porcentaje: null,
  numero_oficinas_atencion: null,
  enlace_notificado_formalmente: null,
  convenio_colaboracion_estado: null,
  personal_area_ti: null,
  infraestructura_firma_electronica: null,
  porcentaje_tramites_en_linea: null,
  porcentaje_tramites_en_linea_no_se_mide: false,
  portal_tramites_tipo: null,
  pagos_electronicos_generalizados: null,
  mecanismo_identidad_estandar: null,
  interoperabilidad_entre_areas: null,
  inventario_sistemas_existe: null,
  politica_gobierno_datos_existe: null,
  respaldos_periodicos_existen: null,
  incidente_ciberseguridad_24meses: null,
  certificacion_seguridad_externa: null,
  rotacion_personal_ti: null,
  dependencia_outsourcing_ti: null,
  mide_tiempos_resolucion: null,
  mide_satisfaccion_ciudadana: null,
  tablero_indicadores_existe: null,
  fondos_digitalizacion_recibidos: null,
  fondos_digitalizacion_detalle: null,
  porcentaje_poblacion_acceso_internet: null,
  porcentaje_poblacion_acceso_internet_no_se_tiene_dato: false,
  accesibilidad_sistemas_discapacidad: null,
  catalogo_tramites_propio_existe: null,
  poblacion_total_fuente: null,
  actualizado_en: null,
};

const PREGUNTA_AREA_TIC =
  "¿El gobierno local cuenta con un área o responsable formalmente designado de tecnologías de la información?";

function renderConQueryClient() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <GobiernoPerfil />
    </QueryClientProvider>,
  );
}

describe("GobiernoPerfil -- autoguardado de un campo booleano", () => {
  beforeEach(() => {
    vi.mocked(obtenerContextoInstitucional).mockResolvedValue(CONTEXTO_VACIO);
    vi.mocked(guardarContextoInstitucional).mockResolvedValue({ ...CONTEXTO_VACIO, area_tic_existe: true });
  });

  it("guarda solo el campo elegido (upsert parcial) al hacer clic en 'Sí', sin botón aparte", async () => {
    const usuario = userEvent.setup();
    renderConQueryClient();

    await screen.findByText(PREGUNTA_AREA_TIC);

    const grupo = screen.getByText(PREGUNTA_AREA_TIC).closest("div")!;
    const opcionSi = within(grupo).getByRole("radio", { name: "Sí" });
    await usuario.click(opcionSi);

    await waitFor(() => {
      expect(guardarContextoInstitucional).toHaveBeenCalledWith({ area_tic_existe: true });
    });
    // Upsert parcial de verdad -- ningún otro campo debe viajar en el payload.
    expect(guardarContextoInstitucional).toHaveBeenCalledTimes(1);
  });

  it("muestra 'Guardando…' mientras la llamada está en curso", async () => {
    let resolver!: (valor: ContextoInstitucionalResponse) => void;
    vi.mocked(guardarContextoInstitucional).mockReturnValue(
      new Promise((resolve) => {
        resolver = resolve;
      }),
    );

    const usuario = userEvent.setup();
    renderConQueryClient();

    await screen.findByText(PREGUNTA_AREA_TIC);
    const grupo = screen.getByText(PREGUNTA_AREA_TIC).closest("div")!;
    await usuario.click(within(grupo).getByRole("radio", { name: "Sí" }));

    await screen.findByText("Guardando…");
    resolver({ ...CONTEXTO_VACIO, area_tic_existe: true });
    await waitFor(() => expect(screen.queryByText("Guardando…")).not.toBeInTheDocument());
  });
});

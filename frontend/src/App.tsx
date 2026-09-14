import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { ProtectedLayout } from "./components/ProtectedLayout";
import { RutaAdmin } from "./components/RutaAdmin";
import { SessionExpiredWatcher } from "./components/SessionExpiredWatcher";
import { AdminSaludIA } from "./pages/AdminSaludIA";
import { AdminUsuarios } from "./pages/AdminUsuarios";
import { ComparadorPlan } from "./pages/ComparadorPlan";
import { Diagnostico } from "./pages/Diagnostico";
import { GobiernoPerfil } from "./pages/GobiernoPerfil";
import { LoginPage } from "./pages/LoginPage";
import { PanelResumen } from "./pages/PanelResumen";
import { Perfil } from "./pages/Perfil";
import { Plan } from "./pages/Plan";
import { Seguimiento } from "./pages/Seguimiento";

const queryClient = new QueryClient();

// Las 6 rutas originales del mapa de docs/app-flow.md líneas 8-15, más dos
// añadidas por RBAC (migración 0011 del backend): "/perfil" (autoservicio de
// cualquier rol) y "/admin/usuarios" (solo admin_gobierno, protegida además por
// RutaAdmin -- ver ese componente para el porqué de por qué esto es solo UX,
// no la barrera de seguridad real).
export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <SessionExpiredWatcher />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedLayout />}>
            <Route path="/" element={<PanelResumen />} />
            <Route path="/tramites/:tramiteId/diagnostico" element={<Diagnostico />} />
            <Route path="/tramites/:tramiteId/plan" element={<Plan />} />
            <Route path="/tramites/:tramiteId/plan/comparar" element={<ComparadorPlan />} />
            <Route path="/seguimiento" element={<Seguimiento />} />
            <Route path="/gobierno/perfil" element={<GobiernoPerfil />} />
            <Route path="/perfil" element={<Perfil />} />
            <Route element={<RutaAdmin />}>
              <Route path="/admin/usuarios" element={<AdminUsuarios />} />
              <Route path="/admin/salud-ia" element={<AdminSaludIA />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

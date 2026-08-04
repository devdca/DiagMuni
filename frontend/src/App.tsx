import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { ProtectedLayout } from "./components/ProtectedLayout";
import { SessionExpiredWatcher } from "./components/SessionExpiredWatcher";
import { Diagnostico } from "./pages/Diagnostico";
import { LoginPage } from "./pages/LoginPage";
import { PanelResumen } from "./pages/PanelResumen";
import { Plan } from "./pages/Plan";
import { Seguimiento } from "./pages/Seguimiento";

const queryClient = new QueryClient();

// Las 5 rutas del mapa de docs/app-flow.md líneas 8-14, ni una más.
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
            <Route path="/seguimiento" element={<Seguimiento />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

import { useEffect, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { sesionValida } from "../lib/session";
import { NavBar } from "./NavBar";

const INTERVALO_REVISION_MS = 30_000;

// Guard de sesión (docs/app-flow.md línea 53): sin sesión válida o con el
// JWT expirado, ninguna de las 4 rutas protegidas es accesible — redirige a
// /login preservando la ruta destino en la query "redirect" para volver ahí
// tras reingresar. La revisión periódica cubre el caso de expiración del JWT
// mientras el funcionario ya está en una pantalla protegida (no solo al
// entrar a la ruta).
export function ProtectedLayout() {
  const location = useLocation();
  const [valida, setValida] = useState(() => sesionValida());

  useEffect(() => {
    const id = setInterval(() => setValida(sesionValida()), INTERVALO_REVISION_MS);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    setValida(sesionValida());
  }, [location.pathname]);

  if (!valida) {
    const destino = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?redirect=${destino}`} replace />;
  }

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="pt-28">
        <Outlet />
      </main>
    </div>
  );
}

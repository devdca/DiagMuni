import { useEffect, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { sesionValida } from "../lib/session";
import { ErrorBoundary } from "./ErrorBoundary";
import { NavBar } from "./NavBar";

const INTERVALO_REVISION_MS = 30_000;

// Guard de sesión -- sin JWT válido redirige a /login preservando la ruta
// destino. La revisión periódica cubre la expiración mientras ya está adentro.
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
      {/* pt-[7.5rem] debe coincidir con la altura real de .app-navbar (index.css) --
          actualizar si el tamaño del logo o el padding del navbar cambian. */}
      <main className="pt-[7.5rem] max-[1200px]:pt-32">
        <ErrorBoundary key={location.pathname}>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  );
}

import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { EVENTO_SESION_EXPIRADA } from "../lib/httpClient";

// Escucha el evento que httpClient dispara ante cualquier 401 del backend
// (no solo el chequeo de "exp" del JWT) y redirige de inmediato a /login
// preservando la ruta destino, sin que cada llamada individual tenga que
// saber cómo navegar.
export function SessionExpiredWatcher() {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    function alExpirar() {
      const destino = encodeURIComponent(location.pathname + location.search);
      void navigate(`/login?redirect=${destino}`, { replace: true });
    }
    window.addEventListener(EVENTO_SESION_EXPIRADA, alExpirar);
    return () => window.removeEventListener(EVENTO_SESION_EXPIRADA, alExpirar);
  }, [location, navigate]);

  return null;
}

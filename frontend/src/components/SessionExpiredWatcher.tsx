import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { EVENTO_SESION_EXPIRADA } from "../lib/httpClient";

// Escucha el 401 global de httpClient y redirige a /login preservando la ruta.
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

import { Navigate, Outlet } from "react-router-dom";

import { esAdmin } from "../lib/session";

// Guard de rol para rutas de admin (va dentro de ProtectedLayout, que ya exige
// sesión). Solo UI: `esAdmin` lee el JWT, pero /api/admin/* siempre revalida el
// rol real contra la base de datos.
export function RutaAdmin() {
  if (!esAdmin()) {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}

import { Navigate, Outlet } from "react-router-dom";

import { esAdmin } from "../lib/session";

// Guard adicional para las rutas de administración (RBAC, migración 0011) --
// va DENTRO de ProtectedLayout (ya exige sesión válida), así que aquí solo hace
// falta el chequeo de rol. Redirige a "/" en vez de mostrar un error: `esAdmin`
// lee el claim del propio JWT solo para decidir qué mostrar, nunca para
// autorizar nada de verdad -- cada endpoint de /api/admin/* vuelve a exigir el
// rol real desde la base de datos (app/adaptadores/http/deps.py::requerir_admin),
// así que un funcionario que fuerce la URL nunca ve datos reales, solo un
// mensaje de "no autorizado" del backend si de algún modo llegara a pedirlos.
export function RutaAdmin() {
  if (!esAdmin()) {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}

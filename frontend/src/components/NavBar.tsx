import { Link, useNavigate } from "react-router-dom";

import { cerrarSesion, obtenerNombreGobierno } from "../lib/session";

// Nav superior fija en toda pantalla con sesión (docs/app-flow.md línea 17):
// nombre del tenant en texto plano (nunca un selector), "Inicio",
// "Perfil del gobierno", "Seguimiento" y "Cerrar sesión". Sin sidebar.
export function NavBar() {
  const navigate = useNavigate();

  function alCerrarSesion() {
    cerrarSesion();
    navigate("/login", { replace: true });
  }

  return (
    <nav>
      <span>{obtenerNombreGobierno()}</span>
      <Link to="/">Inicio</Link>
      <Link to="/gobierno/perfil">Perfil del gobierno</Link>
      <Link to="/seguimiento">Seguimiento</Link>
      <button type="button" onClick={alCerrarSesion}>
        Cerrar sesión
      </button>
    </nav>
  );
}

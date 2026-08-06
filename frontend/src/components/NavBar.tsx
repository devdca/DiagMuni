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
    <nav className="app-navbar">
      <div className="app-navbar-inner">
        <span className="app-navbar-brand">{obtenerNombreGobierno()}</span>
        <div className="app-navbar-links">
          <Link to="/">Inicio</Link>
          <Link to="/gobierno/perfil">Perfil del gobierno</Link>
          <Link to="/seguimiento">Seguimiento</Link>
        </div>
        <button type="button" onClick={alCerrarSesion} className="app-navbar-logout">
          Cerrar sesión
        </button>
      </div>
    </nav>
  );
}

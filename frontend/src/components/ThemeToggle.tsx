import { useEffect, useState } from "react";

import { alternarTema, aplicarTema, obtenerTemaActivo, type Tema } from "@/lib/theme";

function IconoSol() {
  return (
    <svg aria-hidden viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-[18px]">
      <circle cx="10" cy="10" r="3.5" />
      <path d="M10 2.5v2M10 15.5v2M17.5 10h-2M4.5 10h-2M15.1 4.9l-1.4 1.4M6.3 13.7l-1.4 1.4M15.1 15.1l-1.4-1.4M6.3 6.3 4.9 4.9" strokeLinecap="round" />
    </svg>
  );
}

function IconoLuna() {
  return (
    <svg aria-hidden viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-[18px]">
      <path d="M16.5 12.3A6.8 6.8 0 0 1 7.7 3.5a6.8 6.8 0 1 0 8.8 8.8Z" strokeLinejoin="round" />
    </svg>
  );
}

// El <script> bloqueante de index.html ya aplicó la clase antes del primer
// render -- este componente solo LEE el estado activo, nunca decide de cero
// (evita parpadeo).
export function ThemeToggle() {
  const [tema, setTema] = useState<Tema>(() => obtenerTemaActivo());

  // Sigue el tema del sistema solo mientras el funcionario no haya elegido uno propio.
  useEffect(() => {
    const medios = window.matchMedia("(prefers-color-scheme: dark)");
    const alCambiar = () => {
      if (localStorage.getItem("diagmuni_tema")) return;
      const siguiente: Tema = medios.matches ? "dark" : "light";
      aplicarTema(siguiente);
      setTema(siguiente);
    };
    medios.addEventListener("change", alCambiar);
    return () => medios.removeEventListener("change", alCambiar);
  }, []);

  return (
    <button
      type="button"
      className="app-navbar-theme-toggle"
      aria-label={tema === "dark" ? "Cambiar a tema claro" : "Cambiar a tema oscuro"}
      onClick={() => setTema(alternarTema())}
    >
      {tema === "dark" ? <IconoSol /> : <IconoLuna />}
    </button>
  );
}

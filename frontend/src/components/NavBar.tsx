import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { obtenerMiPerfil } from "@/lib/usuariosApi";

import { cerrarSesion, esAdmin, obtenerNombreGobierno } from "../lib/session";
import { NotificacionesBell } from "./NotificacionesBell";

// Íconos de línea puramente decorativos (aria-hidden) -- el texto del enlace ya
// es la etiqueta accesible, el ícono solo ayuda a escanear la barra de un
// vistazo (revisión de diseño, docs/ux-brief.md sección "Principios de diseño").
// size-[18px] en vez de size-4 (16px) -- feedback de que se veían chicos frente
// al resto de la tipografía de la barra.
function IconoInicio() {
  return (
    <svg aria-hidden viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-[18px] shrink-0">
      <path d="M3 9.5 10 4l7 5.5V17a1 1 0 0 1-1 1h-3v-5H7v5H4a1 1 0 0 1-1-1V9.5Z" strokeLinejoin="round" />
    </svg>
  );
}

function IconoPerfilGobierno() {
  return (
    <svg aria-hidden viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-[18px] shrink-0">
      <rect x="4" y="3" width="12" height="14" rx="1" />
      <path d="M7.5 7h1M11.5 7h1M7.5 10h1M11.5 10h1M7.5 13h1M11.5 13h1" />
    </svg>
  );
}

function IconoSeguimiento() {
  return (
    <svg aria-hidden viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-[18px] shrink-0">
      <rect x="3.5" y="3.5" width="13" height="13" rx="1.5" />
      <path d="m6.5 10 2 2 4-4.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconoAdministracion() {
  return (
    <svg aria-hidden viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-[18px] shrink-0">
      <circle cx="10" cy="10" r="2.6" />
      <path
        d="M10 2.5v2M10 15.5v2M17.5 10h-2M4.5 10h-2M15.1 4.9l-1.4 1.4M6.3 13.7l-1.4 1.4M15.1 15.1l-1.4-1.4M6.3 6.3 4.9 4.9"
        strokeLinecap="round"
      />
    </svg>
  );
}

function IconoPerfilSilueta() {
  return (
    <svg aria-hidden viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-4">
      <circle cx="10" cy="7" r="3" />
      <path d="M4 17c0-3 2.7-5 6-5s6 2 6 5" strokeLinecap="round" />
    </svg>
  );
}

function IconoMenu() {
  return (
    <svg aria-hidden viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-[18px] shrink-0">
      <path d="M3 6h14M3 10h14M3 14h14" strokeLinecap="round" />
    </svg>
  );
}

function IconoCerrarSesion() {
  return (
    <svg aria-hidden viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-4 shrink-0">
      <path d="M8 3.5H5a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M13 13.5 16.5 10 13 6.5M16.5 10H8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// Iniciales estilo Microsoft 365 (círculo con 1-2 letras) en vez de un botón de
// texto -- pedido explícito de diseño. "María Pérez" -> "MP"; un solo nombre sin
// espacios usa sus 2 primeras letras; sin nombre cargado todavía (query en vuelo
// o error) cae a la silueta genérica, nunca a un círculo vacío.
function inicialesDeNombre(nombre: string): string {
  const partes = nombre.trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "";
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

// Avatar con menú desplegable estilo Microsoft 365 (clic o Enter/Espacio abre
// el menú -- Radix DropdownMenu ya trae el manejo de teclado/foco) -- reemplaza
// el enlace directo a /perfil y el botón de "Cerrar sesión" que antes vivían
// sueltos en la barra. Feedback de diseño: ahorra espacio y evita que el botón
// de cerrar sesión quede como un bloque de color aparte compitiendo con el
// resto de la barra. Mismo queryKey ["mi-perfil"] que Perfil.tsx y
// AdminUsuarios.tsx -- React Query deduplica/cachea la petición entre los tres,
// no es una llamada extra por cada pantalla que se visita.
function AvatarPerfil() {
  const navigate = useNavigate();
  const perfilQuery = useQuery({ queryKey: ["mi-perfil"], queryFn: obtenerMiPerfil });
  const iniciales = perfilQuery.data ? inicialesDeNombre(perfilQuery.data.nombre) : "";

  function alCerrarSesion() {
    cerrarSesion();
    void navigate("/login", { replace: true });
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="app-navbar-avatar" aria-label="Cuenta">
        {iniciales || <IconoPerfilSilueta />}
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuItem asChild>
          <Link to="/perfil">
            <IconoPerfilSilueta />
            Mi perfil
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={alCerrarSesion}>
          <IconoCerrarSesion />
          Cerrar sesión
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// Mismos 4 enlaces que la barra de escritorio, para el menú de hamburguesa que
// aparece por debajo de 1024px (revisión de QA visual: sin esto, los enlaces
// de texto se envolvían en filas sueltas y desordenadas en vez de colapsar a
// un menú -- DiagMuni sigue siendo desktop-only, pero no debe verse desfasado
// si la ventana de escritorio se reduce).
function MenuMovil() {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="inline-flex size-9 shrink-0 items-center justify-center rounded-md text-foreground hover:bg-secondary lg:hidden"
        aria-label="Abrir menú de navegación"
      >
        <IconoMenu />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        <DropdownMenuItem asChild>
          <Link to="/">
            <IconoInicio />
            Inicio
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link to="/gobierno/perfil">
            <IconoPerfilGobierno />
            Perfil del gobierno
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link to="/seguimiento">
            <IconoSeguimiento />
            Seguimiento
          </Link>
        </DropdownMenuItem>
        {esAdmin() && (
          <DropdownMenuItem asChild>
            <Link to="/admin/usuarios">
              <IconoAdministracion />
              Administración
            </Link>
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// Nav superior fija en toda pantalla con sesión (docs/app-flow.md línea 17):
// nombre del tenant en texto plano (nunca un selector), "Inicio",
// "Perfil del gobierno" y "Seguimiento". Sin sidebar. "Mi perfil" y "Cerrar
// sesión" viven dentro del menú del avatar (AvatarPerfil arriba) -- antes eran
// un enlace y un botón sueltos que amontonaban la barra.
//
// Por debajo de 1024px (`lg`), `.app-navbar-links` se oculta (`hidden
// lg:flex`) y `MenuMovil` toma su lugar -- ver nota de esa función.
export function NavBar() {
  return (
    <nav className="app-navbar">
      <div className="app-navbar-inner">
        <span className="app-navbar-brand">{obtenerNombreGobierno()}</span>
        <div className="app-navbar-links hidden lg:flex">
          <Link to="/">
            <IconoInicio />
            Inicio
          </Link>
          <Link to="/gobierno/perfil">
            <IconoPerfilGobierno />
            Perfil del gobierno
          </Link>
          <Link to="/seguimiento">
            <IconoSeguimiento />
            Seguimiento
          </Link>
          {esAdmin() && (
            <Link to="/admin/usuarios">
              <IconoAdministracion />
              Administración
            </Link>
          )}
        </div>
        <div className="flex items-center gap-4">
          <MenuMovil />
          <NotificacionesBell />
          <AvatarPerfil />
        </div>
      </div>
    </nav>
  );
}

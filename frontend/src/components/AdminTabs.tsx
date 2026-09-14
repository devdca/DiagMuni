import { Link } from "react-router-dom";

import { cn } from "@/lib/utils";

// Sub-navegación entre las pantallas de administración (/admin/usuarios,
// /admin/salud-ia) -- ambas ya están protegidas por RutaAdmin, esto es solo la
// forma de moverse entre ellas sin volver al panel resumen.
export function AdminTabs({ activa }: { activa: "usuarios" | "salud-ia" }) {
  const tabs = [
    { valor: "usuarios" as const, etiqueta: "Usuarios y roles", ruta: "/admin/usuarios" },
    { valor: "salud-ia" as const, etiqueta: "Salud del sistema", ruta: "/admin/salud-ia" },
  ];

  return (
    <div className="inline-flex w-fit gap-1 rounded-md bg-secondary p-1">
      {tabs.map((tab) => (
        <Link
          key={tab.valor}
          to={tab.ruta}
          className={cn(
            "inline-flex min-h-9 items-center justify-center rounded-sm px-3 py-1.5 text-sm font-medium transition-colors",
            tab.valor === activa
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {tab.etiqueta}
        </Link>
      ))}
    </div>
  );
}

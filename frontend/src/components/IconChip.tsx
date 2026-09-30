import type { ReactNode } from "react";

// Insignia de ícono compartida (cuadro con borde + ícono de línea) entre
// PageHeader ("md") y títulos de tarjeta que quieren la misma identidad ("sm").
const TAMANOS = {
  sm: "size-8 rounded-lg",
  md: "size-11 rounded-xl",
} as const;

export function IconChip({ icon, size = "md" }: { icon: ReactNode; size?: keyof typeof TAMANOS }) {
  return (
    <span
      className={`flex ${TAMANOS[size]} shrink-0 items-center justify-center border border-border bg-card text-foreground`}
    >
      {icon}
    </span>
  );
}

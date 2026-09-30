import type { ReactNode } from "react";

import { IconChip } from "./IconChip";

// Identidad visual por sección: ícono en tinta neutra (nunca el azul de la
// rampa de madurez, ese ya tiene su propio significado) + rótulo sobre el título.
export function PageHeader({ icon, kicker, title }: { icon: ReactNode; kicker?: string; title: string }) {
  return (
    <div className="flex flex-col gap-2">
      {kicker && (
        <span className="text-[0.68rem] font-bold tracking-[0.1em] text-muted-foreground uppercase">{kicker}</span>
      )}
      <div className="flex items-center gap-3">
        <IconChip icon={icon} size="md" />
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
      </div>
    </div>
  );
}

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

// shadcn/ui (MIT, docs/stack-tecnologico.md línea 25), código copiado al repo.
// Sin soporte `asChild`/Radix Slot: ningún caso de este brief necesita renderizar
// el botón como otro elemento (ej. un <Link>) -- se agrega @radix-ui/react-slot
// solo si un caso futuro lo requiere de verdad (reutilizar antes que construir,
// pero también instalar solo lo que la tarea necesita).
const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-md text-sm font-medium whitespace-nowrap transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        outline: "border border-input bg-background hover:bg-secondary",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-secondary hover:text-secondary-foreground",
      },
      size: {
        default: "h-10 px-4 py-2 min-h-[44px]", // objetivo de toque >= 44px, docs/ux-brief.md "Accesibilidad"
        sm: "h-9 px-3",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ComponentProps<"button">,
    VariantProps<typeof buttonVariants> {}

function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button data-slot="button" className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}

export { Button, buttonVariants };

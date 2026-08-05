import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

// shadcn/ui (MIT, docs/stack-tecnologico.md línea 25), código copiado al repo.
// Regla dura de docs/ux-brief.md, "Índice de madurez" y "Semáforo de seguimiento":
// un badge nunca es solo color -- cada uso concreto (ver frontend/src/lib/madurez.ts)
// siempre acompaña el color con número y/o etiqueta de texto.
const badgeVariants = cva(
  "inline-flex w-fit items-center gap-1.5 rounded-full border border-transparent px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground",
        secondary: "bg-secondary text-secondary-foreground",
        outline: "border-border text-foreground",
      },
    },
    defaultVariants: {
      variant: "secondary",
    },
  },
);

export interface BadgeProps extends React.ComponentProps<"span">, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span data-slot="badge" className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };

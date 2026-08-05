import * as React from "react";

import { cn } from "@/lib/utils";

// shadcn/ui (MIT, docs/stack-tecnologico.md línea 25), código copiado al repo.
// Sin primitiva de Radix: es un <textarea> nativo estilizado, igual que el
// componente de referencia de shadcn/ui.
function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground outline-none placeholder:text-atenuado focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive",
        className,
      )}
      {...props}
    />
  );
}

export { Textarea };

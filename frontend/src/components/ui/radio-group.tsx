import * as React from "react";
import * as RadioGroupPrimitive from "@radix-ui/react-radio-group";

import { cn } from "@/lib/utils";

// shadcn/ui (MIT, docs/stack-tecnologico.md línea 25), código copiado al repo.
// Primitiva real de Radix (@radix-ui/react-radio-group, MIT -- verificado en
// node_modules/@radix-ui/react-radio-group/LICENSE).
function RadioGroup({ className, ...props }: React.ComponentProps<typeof RadioGroupPrimitive.Root>) {
  return <RadioGroupPrimitive.Root data-slot="radio-group" className={cn("grid gap-3", className)} {...props} />;
}

function RadioGroupItem({ className, ...props }: React.ComponentProps<typeof RadioGroupPrimitive.Item>) {
  return (
    <RadioGroupPrimitive.Item
      data-slot="radio-group-item"
      className={cn(
        // QA (ronda 2, hallazgo #3): el indicador nunca se veía -- su único
        // hijo estaba en `absolute`, así que no le daba tamaño al contenedor
        // flex del indicador (colapsaba a height:0). Ahora el indicador llena
        // el propio botón (`size-full`, ya no `relative`+`absolute`) y,
        // además del punto, el borde también cambia de color al seleccionar
        // -- dos señales visuales, no una sola que dependía de un bug.
        "aspect-square size-5 shrink-0 rounded-full border border-input bg-background outline-none transition-colors focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:border-primary",
        className,
      )}
      {...props}
    >
      <RadioGroupPrimitive.Indicator data-slot="radio-group-indicator" className="flex size-full items-center justify-center">
        <span className="radio-indicador-animado size-2.5 rounded-full bg-primary" />
      </RadioGroupPrimitive.Indicator>
    </RadioGroupPrimitive.Item>
  );
}

export { RadioGroup, RadioGroupItem };

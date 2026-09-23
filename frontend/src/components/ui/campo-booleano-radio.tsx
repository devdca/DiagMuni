import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { cn } from "@/lib/utils";

// RadioGroup Sí/No compartido por las preguntas booleanas del cuestionario de
// diagnóstico y el perfil de gobierno -- antes duplicado en 4 lugares
// (Diagnostico.tsx: CardBooleana, CardVariableAdicional, CardTramiteConcurrente;
// GobiernoPerfil.tsx: CampoBooleano). `idPrefix` arma los `id`/`htmlFor` únicos
// de cada opción (`${idPrefix}-si` / `${idPrefix}-no`).
export function CampoBooleanoRadio({
  valor,
  onCambiar,
  idPrefix,
}: {
  valor: boolean | null;
  onCambiar: (valor: boolean) => void;
  idPrefix: string;
}) {
  return (
    <RadioGroup
      value={valor === null ? undefined : valor ? "si" : "no"}
      onValueChange={(v) => onCambiar(v === "si")}
      className="grid grid-cols-2 gap-3 sm:w-64"
    >
      {(["si", "no"] as const).map((opcion) => (
        <label
          key={opcion}
          htmlFor={`${idPrefix}-${opcion}`}
          className={cn(
            "flex min-h-11 cursor-pointer items-center gap-3 rounded-md border px-3 py-2",
            (valor === true && opcion === "si") || (valor === false && opcion === "no")
              ? "border-primary"
              : "border-border",
          )}
        >
          <RadioGroupItem value={opcion} id={`${idPrefix}-${opcion}`} />
          <span className="text-sm">{opcion === "si" ? "Sí" : "No"}</span>
        </label>
      ))}
    </RadioGroup>
  );
}

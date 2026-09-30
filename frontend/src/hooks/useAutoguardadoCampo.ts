import { useEffect, useRef, useState } from "react";

export type EstadoAutoguardado = "inactivo" | "guardando" | "guardado" | "error";

// Dispara `guardar(valor)` `debounceMs` después de que `valor` deje de
// cambiar, cancelando el timer si vuelve a cambiar antes o si se desmonta. No
// dispara en el render inicial -- la carga inicial de datos del servidor
// nunca debe volver a guardarse a sí misma. Usado en Diagnostico.tsx y GobiernoPerfil.tsx.
export function useAutoguardadoCampo<T>(
  valor: T,
  guardar: (valor: T) => Promise<unknown>,
  debounceMs = 1000,
): EstadoAutoguardado {
  const [estado, setEstado] = useState<EstadoAutoguardado>("inactivo");
  const guardarRef = useRef(guardar);
  guardarRef.current = guardar;
  const montadoPreviamenteRef = useRef(false);

  useEffect(() => {
    if (!montadoPreviamenteRef.current) {
      montadoPreviamenteRef.current = true;
      return;
    }

    let cancelado = false;
    const idTimer = setTimeout(() => {
      setEstado("guardando");
      guardarRef
        .current(valor)
        .then(() => {
          if (!cancelado) setEstado("guardado");
        })
        .catch(() => {
          if (!cancelado) setEstado("error");
        });
    }, debounceMs);

    return () => {
      cancelado = true;
      clearTimeout(idTimer);
    };
  }, [valor, debounceMs]);

  return estado;
}

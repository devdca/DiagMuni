import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { obtenerLogoGobierno } from "./logoGobiernoApi";

// El blob se cachea vía TanStack Query (una sola descarga real); el object URL
// no se cachea -- cada consumidor crea el suyo y lo revoca al desmontar/cambiar,
// para no filtrar memoria.
export function useLogoGobiernoUrl(): string | null {
  const { data: blob } = useQuery({ queryKey: ["logo-gobierno"], queryFn: obtenerLogoGobierno });
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!blob) {
      setUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(blob);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [blob]);

  return url;
}

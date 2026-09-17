// El logo no viaja en el JWT (a diferencia de `nombre_gobierno`): es un archivo
// reemplazable, se consulta aparte. GET devuelve el archivo crudo, no JSON --
// por eso `fetch` directo en vez de `apiFetch`. 404 = "sin logo todavía", estado
// válido, no un error.

import { obtenerToken } from "./session";

export async function obtenerLogoGobierno(): Promise<Blob | null> {
  const token = obtenerToken();
  const respuesta = await fetch("/api/gobierno/logo", {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (respuesta.status === 404) return null;
  if (!respuesta.ok) throw new Error("No se pudo cargar el logo del gobierno.");
  return respuesta.blob();
}

// Requiere admin_gobierno -- un funcionario raso ve el logo pero no lo reemplaza.
export async function subirLogoGobierno(archivo: File): Promise<void> {
  const token = obtenerToken();
  const formData = new FormData();
  formData.append("archivo", archivo);
  const respuesta = await fetch("/api/gobierno/logo", {
    method: "PUT",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!respuesta.ok) {
    const detalle: unknown = await respuesta.json().catch(() => null);
    const mensaje =
      detalle && typeof detalle === "object" && "detail" in detalle && typeof detalle.detail === "string"
        ? detalle.detail
        : "No se pudo subir el logo.";
    throw new Error(mensaje);
  }
}

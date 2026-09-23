import { apiFetch } from "./httpClient";

// Centro de notificaciones tenant-wide, sin destinatario individual.
export interface NotificacionResponse {
  id: string;
  tipo: string;
  titulo: string;
  mensaje: string;
  tramite_id: string | null;
  leida: boolean;
  creado_en: string;
}

export interface ListaNotificacionesResponse {
  notificaciones: NotificacionResponse[];
  no_leidas: number;
}

export function listarNotificaciones(): Promise<ListaNotificacionesResponse> {
  return apiFetch<ListaNotificacionesResponse>("/api/notificaciones");
}

export function marcarNotificacionLeida(id: string): Promise<NotificacionResponse> {
  return apiFetch<NotificacionResponse>(`/api/notificaciones/${id}/leer`, { method: "POST" });
}

export function marcarTodasLeidas(): Promise<void> {
  return apiFetch<void>("/api/notificaciones/marcar-todas-leidas", { method: "POST" });
}

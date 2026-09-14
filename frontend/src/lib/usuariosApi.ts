import { apiFetch } from "./httpClient";

// Espejo de backend/app/schemas/usuario.py -- RBAC (migración 0011). Dos rutas:
// /api/usuarios/me (autoservicio, cualquier rol) y /api/admin/usuarios (gestión
// de otros usuarios, solo admin_gobierno).
export type RolUsuario = "funcionario" | "admin_gobierno";

export interface UsuarioResponse {
  id: string;
  nombre: string;
  email: string;
  rol: RolUsuario;
  activo: boolean;
  ultimo_login_en: string | null;
  created_at: string;
}

export interface UsuarioConPasswordResponse {
  usuario: UsuarioResponse;
  password_temporal: string;
}

// --- Autoservicio (cualquier rol autenticado) -------------------------------

export function obtenerMiPerfil(): Promise<UsuarioResponse> {
  return apiFetch<UsuarioResponse>("/api/usuarios/me");
}

export function actualizarMiPerfil(nombre: string): Promise<UsuarioResponse> {
  return apiFetch<UsuarioResponse>("/api/usuarios/me", {
    method: "PATCH",
    body: JSON.stringify({ nombre }),
  });
}

export function cambiarMiPassword(passwordActual: string, passwordNueva: string): Promise<void> {
  return apiFetch<void>("/api/usuarios/me/password", {
    method: "POST",
    body: JSON.stringify({ password_actual: passwordActual, password_nueva: passwordNueva }),
  });
}

// --- Administración de usuarios (solo admin_gobierno) -----------------------

export function listarUsuarios(): Promise<UsuarioResponse[]> {
  return apiFetch<UsuarioResponse[]>("/api/admin/usuarios");
}

export interface CrearUsuarioPayload {
  nombre: string;
  email: string;
  rol: RolUsuario;
}

export function crearUsuario(payload: CrearUsuarioPayload): Promise<UsuarioConPasswordResponse> {
  return apiFetch<UsuarioConPasswordResponse>("/api/admin/usuarios", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function desactivarUsuario(usuarioId: string): Promise<UsuarioResponse> {
  return apiFetch<UsuarioResponse>(`/api/admin/usuarios/${usuarioId}/desactivar`, { method: "POST" });
}

export function reactivarUsuario(usuarioId: string): Promise<UsuarioResponse> {
  return apiFetch<UsuarioResponse>(`/api/admin/usuarios/${usuarioId}/reactivar`, { method: "POST" });
}

export function cambiarRolUsuario(usuarioId: string, rol: RolUsuario): Promise<UsuarioResponse> {
  return apiFetch<UsuarioResponse>(`/api/admin/usuarios/${usuarioId}/rol`, {
    method: "PATCH",
    body: JSON.stringify({ rol }),
  });
}

export interface ResetearPasswordResponse {
  password_temporal: string;
}

export function resetearPasswordUsuario(usuarioId: string): Promise<ResetearPasswordResponse> {
  return apiFetch<ResetearPasswordResponse>(`/api/admin/usuarios/${usuarioId}/resetear-password`, {
    method: "POST",
  });
}

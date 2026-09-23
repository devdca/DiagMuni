import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { AdminTabs } from "@/components/AdminTabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/httpClient";
import {
  cambiarRolUsuario,
  crearUsuario,
  desactivarUsuario,
  listarUsuarios,
  reactivarUsuario,
  resetearPasswordUsuario,
  type RolUsuario,
  type UsuarioResponse,
} from "@/lib/usuariosApi";
import { obtenerMiPerfil } from "@/lib/usuariosApi";

// "Usuarios y roles" -- solo admin_gobierno, protegido en App.tsx y en cada
// endpoint del backend.

function formatearFecha(fechaIso: string | null): string {
  if (!fechaIso) return "Nunca";
  return new Date(fechaIso).toLocaleDateString("es", { year: "numeric", month: "short", day: "numeric" });
}

// El backend rechaza desactivar al último admin_gobierno activo con un 400 en
// lenguaje llano -- se muestra tal cual, sin adivinar la regla en el cliente.
function mensajeError(error: unknown, generico: string): string {
  return error instanceof ApiError ? error.message : generico;
}

function PasswordTemporalAviso({ etiqueta, password }: { etiqueta: string; password: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-md border border-border bg-secondary/40 p-3 text-sm">
      <span className="font-medium">{etiqueta}</span>
      <code className="w-fit rounded bg-background px-2 py-1 font-mono text-sm">{password}</code>
      <span className="text-xs text-atenuado">No se vuelve a mostrar -- anótala ahora.</span>
    </div>
  );
}

function FormularioNuevoUsuario({ abierto, onCerrar }: { abierto: boolean; onCerrar: () => void }) {
  const queryClient = useQueryClient();
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [rol, setRol] = useState<RolUsuario>("funcionario");
  const [passwordGenerada, setPasswordGenerada] = useState<string | null>(null);

  const crearMutacion = useMutation({
    mutationFn: crearUsuario,
    onSuccess: (respuesta) => {
      void queryClient.invalidateQueries({ queryKey: ["admin-usuarios"] });
      setPasswordGenerada(respuesta.password_temporal);
      setNombre("");
      setEmail("");
      setRol("funcionario");
    },
  });

  if (!abierto) return null;

  if (passwordGenerada) {
    return (
      <div className="mb-4 flex flex-col gap-3 rounded-md border border-border p-4">
        <PasswordTemporalAviso etiqueta="Contraseña de arranque del nuevo usuario" password={passwordGenerada} />
        <div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setPasswordGenerada(null);
              onCerrar();
            }}
          >
            Cerrar
          </Button>
        </div>
      </div>
    );
  }

  return (
    <form
      className="mb-4 flex flex-col gap-3 rounded-md border border-border p-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (nombre.trim() === "" || email.trim() === "") return;
        crearMutacion.mutate({ nombre: nombre.trim(), email: email.trim(), rol });
      }}
    >
      <div className="flex flex-col gap-2">
        <label htmlFor="nuevo-usuario-nombre" className="text-sm font-medium">
          Nombre
        </label>
        <Input id="nuevo-usuario-nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor="nuevo-usuario-email" className="text-sm font-medium">
          Correo
        </label>
        <Input
          id="nuevo-usuario-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </div>
      <div className="flex flex-col gap-2">
        <label htmlFor="nuevo-usuario-rol" className="text-sm font-medium">
          Rol
        </label>
        <select
          id="nuevo-usuario-rol"
          value={rol}
          onChange={(e) => setRol(e.target.value as RolUsuario)}
          className="min-h-[44px] rounded-md border border-input bg-background px-2 text-sm text-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          <option value="funcionario">Funcionario</option>
          <option value="admin_gobierno">Administrador</option>
        </select>
      </div>
      {crearMutacion.isError && (
        <p className="text-xs text-destructive">{mensajeError(crearMutacion.error, "No se pudo agregar el usuario.")}</p>
      )}
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={crearMutacion.isPending}>
          {crearMutacion.isPending ? "Guardando..." : "Agregar usuario"}
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={onCerrar}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}

function FilaUsuario({ usuario, esYoMismo }: { usuario: UsuarioResponse; esYoMismo: boolean }) {
  const queryClient = useQueryClient();
  const invalidar = () => void queryClient.invalidateQueries({ queryKey: ["admin-usuarios"] });
  const [passwordReseteada, setPasswordReseteada] = useState<string | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);

  const desactivarMutacion = useMutation({
    mutationFn: () => desactivarUsuario(usuario.id),
    onSuccess: () => {
      setErrorAccion(null);
      invalidar();
    },
    onError: (error: unknown) => setErrorAccion(mensajeError(error, "No se pudo desactivar.")),
  });

  const reactivarMutacion = useMutation({ mutationFn: () => reactivarUsuario(usuario.id), onSuccess: invalidar });

  const cambiarRolMutacion = useMutation({
    mutationFn: (nuevoRol: RolUsuario) => cambiarRolUsuario(usuario.id, nuevoRol),
    onSuccess: () => {
      setErrorAccion(null);
      invalidar();
    },
    onError: (error: unknown) => setErrorAccion(mensajeError(error, "No se pudo cambiar el rol.")),
  });

  const resetearMutacion = useMutation({
    mutationFn: () => resetearPasswordUsuario(usuario.id),
    onSuccess: (respuesta) => setPasswordReseteada(respuesta.password_temporal),
  });

  return (
    <>
      <tr className="border-b border-border last:border-0">
        <td className="py-3 pr-4">
          {usuario.nombre}
          {esYoMismo && <span className="ml-2 text-xs text-atenuado">(tú)</span>}
        </td>
        <td className="py-3 pr-4 text-muted-foreground">{usuario.email}</td>
        <td className="py-3 pr-4">
          <select
            value={usuario.rol}
            disabled={cambiarRolMutacion.isPending}
            onChange={(e) => cambiarRolMutacion.mutate(e.target.value as RolUsuario)}
            className="min-h-9 rounded-md border border-input bg-background px-2 text-sm text-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
          >
            <option value="funcionario">Funcionario</option>
            <option value="admin_gobierno">Administrador</option>
          </select>
        </td>
        <td className="py-3 pr-4">
          {usuario.activo ? (
            <Badge variant="outline">Activo</Badge>
          ) : (
            <Badge variant="secondary">Inactivo</Badge>
          )}
        </td>
        <td className="py-3 pr-4 text-muted-foreground">{formatearFecha(usuario.ultimo_login_en)}</td>
        <td className="py-3 text-right">
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="outline" disabled={resetearMutacion.isPending} onClick={() => resetearMutacion.mutate()}>
              Resetear contraseña
            </Button>
            {usuario.activo ? (
              <Button size="sm" variant="outline" disabled={desactivarMutacion.isPending} onClick={() => desactivarMutacion.mutate()}>
                Desactivar
              </Button>
            ) : (
              <Button size="sm" variant="outline" disabled={reactivarMutacion.isPending} onClick={() => reactivarMutacion.mutate()}>
                Reactivar
              </Button>
            )}
          </div>
        </td>
      </tr>
      {(errorAccion || passwordReseteada) && (
        <tr>
          <td colSpan={6} className="pb-3">
            {errorAccion && <p className="text-xs text-destructive">{errorAccion}</p>}
            {passwordReseteada && (
              <PasswordTemporalAviso etiqueta={`Nueva contraseña para ${usuario.email}`} password={passwordReseteada} />
            )}
          </td>
        </tr>
      )}
    </>
  );
}

export function AdminUsuarios() {
  const [formularioAbierto, setFormularioAbierto] = useState(false);
  const usuariosQuery = useQuery({ queryKey: ["admin-usuarios"], queryFn: listarUsuarios });
  const miPerfilQuery = useQuery({ queryKey: ["mi-perfil"], queryFn: obtenerMiPerfil });

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 p-6">
      <div>
        <h2 className="text-lg font-semibold">Administración del gobierno</h2>
        <p className="text-sm text-muted-foreground">
          Alta, roles y estado de los funcionarios de tu gobierno -- solo visible para el rol Administrador.
        </p>
      </div>

      <AdminTabs activa="usuarios" />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle>Usuarios</CardTitle>
          {!formularioAbierto && (
            <Button size="sm" variant="outline" onClick={() => setFormularioAbierto(true)}>
              Agregar usuario
            </Button>
          )}
        </CardHeader>
        <CardContent>
          <FormularioNuevoUsuario abierto={formularioAbierto} onCerrar={() => setFormularioAbierto(false)} />

          {usuariosQuery.isLoading && <p className="text-sm text-atenuado">Cargando...</p>}
          {usuariosQuery.isError && <p className="text-sm text-destructive">No se pudo cargar la lista de usuarios.</p>}

          {usuariosQuery.data && (
            // Scroll horizontal propio (ver AdminSaludIA.tsx).
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-muted-foreground">
                    <th className="py-2 font-medium">Nombre</th>
                    <th className="py-2 font-medium">Correo</th>
                    <th className="py-2 font-medium">Rol</th>
                    <th className="py-2 font-medium">Estado</th>
                    <th className="py-2 font-medium">Último acceso</th>
                    <th className="py-2 pr-0 text-right font-medium">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {usuariosQuery.data.map((usuario) => (
                    <FilaUsuario
                      key={usuario.id}
                      usuario={usuario}
                      esYoMismo={usuario.id === miPerfilQuery.data?.id}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/httpClient";
import { actualizarMiPerfil, cambiarMiPassword, obtenerMiPerfil } from "@/lib/usuariosApi";

// "Mi perfil": autoservicio del propio usuario -- distinto de "Perfil del
// gobierno", que es el contexto institucional del tenant.

function etiquetaRol(rol: string): string {
  return rol === "admin_gobierno" ? "Administrador" : "Funcionario";
}

function iniciales(nombre: string): string {
  const partes = nombre.trim().split(/\s+/);
  const primeras = partes.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "");
  return primeras.join("") || "?";
}

export function Perfil() {
  const queryClient = useQueryClient();
  const perfilQuery = useQuery({ queryKey: ["mi-perfil"], queryFn: obtenerMiPerfil });

  const [nombre, setNombre] = useState("");
  useEffect(() => {
    if (perfilQuery.data) setNombre(perfilQuery.data.nombre);
  }, [perfilQuery.data]);

  const guardarNombreMutacion = useMutation({
    mutationFn: (valor: string) => actualizarMiPerfil(valor),
    onSuccess: (respuesta) => queryClient.setQueryData(["mi-perfil"], respuesta),
  });

  const [passwordActual, setPasswordActual] = useState("");
  const [passwordNueva, setPasswordNueva] = useState("");
  const [passwordConfirmar, setPasswordConfirmar] = useState("");
  const [errorPassword, setErrorPassword] = useState<string | null>(null);
  const [passwordCambiada, setPasswordCambiada] = useState(false);

  const cambiarPasswordMutacion = useMutation({
    mutationFn: () => cambiarMiPassword(passwordActual, passwordNueva),
    onSuccess: () => {
      setPasswordActual("");
      setPasswordNueva("");
      setPasswordConfirmar("");
      setErrorPassword(null);
      setPasswordCambiada(true);
    },
    onError: (error: unknown) => {
      setPasswordCambiada(false);
      setErrorPassword(error instanceof ApiError ? error.message : "No se pudo cambiar la contraseña.");
    },
  });

  function enviarCambioPassword(e: React.FormEvent) {
    e.preventDefault();
    setPasswordCambiada(false);
    if (passwordNueva.length < 12) {
      setErrorPassword("La contraseña nueva debe tener al menos 12 caracteres.");
      return;
    }
    if (passwordNueva !== passwordConfirmar) {
      setErrorPassword("La confirmación no coincide con la contraseña nueva.");
      return;
    }
    setErrorPassword(null);
    cambiarPasswordMutacion.mutate();
  }

  if (perfilQuery.isLoading) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-sm text-atenuado">Cargando...</p>
      </div>
    );
  }

  if (perfilQuery.isError || !perfilQuery.data) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-sm text-destructive">No se pudo cargar tu perfil.</p>
      </div>
    );
  }

  const perfil = perfilQuery.data;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
      <div>
        <h2 className="text-lg font-semibold">Mi perfil</h2>
        <p className="text-sm text-muted-foreground">Tus propios datos y contraseña -- no los del gobierno.</p>
      </div>

      <Card>
        <CardContent className="flex items-center gap-4 pt-6">
          <span className="flex size-14 shrink-0 items-center justify-center rounded-full bg-primary text-lg font-semibold text-primary-foreground">
            {iniciales(perfil.nombre)}
          </span>
          <div className="flex flex-col gap-1">
            <span className="font-semibold">{perfil.nombre}</span>
            <span className="text-sm text-muted-foreground">{perfil.email}</span>
            <Badge variant="outline" className="w-fit">
              {etiquetaRol(perfil.rol)}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Datos personales</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label htmlFor="perfil-nombre" className="text-sm font-medium">
              Nombre completo
            </label>
            <Input id="perfil-nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} />
          </div>
          {guardarNombreMutacion.isError && (
            <p className="text-xs text-destructive">No se pudo guardar el nombre. Intenta de nuevo.</p>
          )}
          {guardarNombreMutacion.isSuccess && !guardarNombreMutacion.isPending && (
            <p className="text-xs text-atenuado">Guardado.</p>
          )}
          <div>
            <Button
              size="sm"
              variant="outline"
              disabled={nombre.trim() === "" || nombre === perfil.nombre || guardarNombreMutacion.isPending}
              onClick={() => guardarNombreMutacion.mutate(nombre.trim())}
            >
              {guardarNombreMutacion.isPending ? "Guardando..." : "Guardar cambios"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Seguridad</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={enviarCambioPassword}>
            <div className="flex flex-col gap-2">
              <label htmlFor="password-actual" className="text-sm font-medium">
                Contraseña actual
              </label>
              <Input
                id="password-actual"
                type="password"
                value={passwordActual}
                onChange={(e) => setPasswordActual(e.target.value)}
                required
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="flex flex-col gap-2">
                <label htmlFor="password-nueva" className="text-sm font-medium">
                  Nueva contraseña
                </label>
                <Input
                  id="password-nueva"
                  type="password"
                  placeholder="Mínimo 12 caracteres"
                  value={passwordNueva}
                  onChange={(e) => setPasswordNueva(e.target.value)}
                  required
                />
              </div>
              <div className="flex flex-col gap-2">
                <label htmlFor="password-confirmar" className="text-sm font-medium">
                  Confirmar nueva contraseña
                </label>
                <Input
                  id="password-confirmar"
                  type="password"
                  value={passwordConfirmar}
                  onChange={(e) => setPasswordConfirmar(e.target.value)}
                  required
                />
              </div>
            </div>
            {errorPassword && <p className="text-xs text-destructive">{errorPassword}</p>}
            {passwordCambiada && <p className="text-xs text-atenuado">Contraseña actualizada.</p>}
            <div>
              <Button type="submit" size="sm" disabled={cambiarPasswordMutacion.isPending}>
                {cambiarPasswordMutacion.isPending ? "Actualizando..." : "Actualizar contraseña"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

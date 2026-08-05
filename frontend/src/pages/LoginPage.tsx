import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import { login } from "../lib/authApi";
import { resolverGobierno } from "../lib/gobiernosApi";
import { ApiError } from "../lib/httpClient";
import { guardarSesion } from "../lib/session";

// Pantalla 1 (docs/ux-brief.md, "1. Selección de gobierno (tenant) e ingreso";
// mecanismo completo en entregables/fase-2/identificacion-gobierno-login.md):
// el funcionario escribe la clave de su gobierno, el frontend la resuelve contra
// el backend y solo entonces revela correo/contraseña -- el tenant_id que se
// termina enviando a POST /api/auth/login es siempre el que devolvió el backend,
// nunca algo que el funcionario haya escrito a mano.
interface GobiernoResuelto {
  tenantId: string;
  nombre: string;
}

export function LoginPage() {
  const [clave, setClave] = useState("");
  const [gobierno, setGobierno] = useState<GobiernoResuelto | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const navigate = useNavigate();
  const location = useLocation();

  const resolverMutacion = useMutation({
    mutationFn: resolverGobierno,
    onSuccess: (respuesta) => setGobierno({ tenantId: respuesta.tenant_id, nombre: respuesta.nombre }),
  });

  const loginMutacion = useMutation({
    mutationFn: login,
    onSuccess: (respuesta) => {
      guardarSesion(respuesta.access_token);
      const destino = new URLSearchParams(location.search).get("redirect") || "/";
      navigate(destino, { replace: true });
    },
  });

  function alConfirmarGobierno(evento: FormEvent) {
    evento.preventDefault();
    resolverMutacion.mutate(clave.trim());
  }

  function alCambiarGobierno() {
    setGobierno(null);
    resolverMutacion.reset();
  }

  function alEnviarCredenciales(evento: FormEvent) {
    evento.preventDefault();
    if (!gobierno) return;
    loginMutacion.mutate({ tenant_id: gobierno.tenantId, email: email.trim(), password });
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-xl">DiagMuni</CardTitle>
          <CardDescription>Diagnóstico de modernización municipal</CardDescription>
        </CardHeader>
        <CardContent>
          {!gobierno ? (
            <form onSubmit={alConfirmarGobierno} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="clave-gobierno" className="text-sm font-medium">
                  Clave del gobierno
                </label>
                <Input
                  id="clave-gobierno"
                  type="text"
                  value={clave}
                  onChange={(e) => setClave(e.target.value)}
                  aria-invalid={resolverMutacion.isError}
                  required
                  autoFocus
                />
                <p className="text-xs text-atenuado">
                  Tu propio gobierno te entrega esta clave al darte de alta, junto a tu correo y contraseña.
                </p>
              </div>
              {resolverMutacion.isError && (
                <p role="alert" className="text-sm text-destructive">
                  {resolverMutacion.error instanceof ApiError
                    ? resolverMutacion.error.message
                    : "No se pudo completar la búsqueda. Intenta de nuevo."}
                </p>
              )}
              <Button type="submit" disabled={resolverMutacion.isPending}>
                {resolverMutacion.isPending ? "Buscando..." : "Continuar"}
              </Button>
            </form>
          ) : (
            <form onSubmit={alEnviarCredenciales} className="flex flex-col gap-4">
              <div className="rounded-md bg-secondary px-3 py-2 text-sm">
                <p className="text-atenuado">Vas a ingresar a</p>
                <p className="font-medium">{gobierno.nombre}</p>
                <button
                  type="button"
                  onClick={alCambiarGobierno}
                  className="mt-1 text-xs text-muted-foreground underline"
                >
                  No es tu gobierno, cambiar clave
                </button>
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="email" className="text-sm font-medium">
                  Correo electrónico
                </label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoFocus
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="password" className="text-sm font-medium">
                  Contraseña
                </label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  aria-invalid={loginMutacion.isError}
                  required
                />
              </div>
              {loginMutacion.isError && (
                <p role="alert" className="text-sm text-destructive">
                  {loginMutacion.error instanceof ApiError
                    ? loginMutacion.error.message
                    : "No se pudo completar el ingreso. Intenta de nuevo."}
                </p>
              )}
              <Button type="submit" disabled={loginMutacion.isPending}>
                {loginMutacion.isPending ? "Ingresando..." : "Ingresar"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

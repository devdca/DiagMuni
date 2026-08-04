import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import { login } from "../lib/authApi";
import { ApiError } from "../lib/httpClient";
import { guardarSesion } from "../lib/session";

// Login mínimo funcional de F1: la pantalla real de "selección de gobierno e
// ingreso" (docs/ux-brief.md, pantalla 1) es trabajo de F2. Este formulario
// solo existe para poder probar el guard de sesión de punta a punta.
//
// "Nombre a mostrar" es texto libre sin validar contra el backend — no existe
// hoy ningún endpoint que resuelva el nombre del tenant a partir del
// tenant_id (ver limitación conocida documentada para F2).
export function LoginPage() {
  const [claveGobierno, setClaveGobierno] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nombreAMostrar, setNombreAMostrar] = useState("");

  const navigate = useNavigate();
  const location = useLocation();

  const mutacion = useMutation({
    mutationFn: login,
    onSuccess: (respuesta) => {
      guardarSesion(respuesta.access_token, nombreAMostrar);
      const destino = new URLSearchParams(location.search).get("redirect") || "/";
      navigate(destino, { replace: true });
    },
  });

  function alEnviar(evento: FormEvent) {
    evento.preventDefault();
    mutacion.mutate({ tenant_id: claveGobierno.trim(), email: email.trim(), password });
  }

  return (
    <div>
      <h1>DiagMuni</h1>
      <form onSubmit={alEnviar}>
        <div>
          <label htmlFor="clave-gobierno">Clave del gobierno</label>
          <br />
          <input
            id="clave-gobierno"
            type="text"
            value={claveGobierno}
            onChange={(e) => setClaveGobierno(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="email">Correo electrónico</label>
          <br />
          <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <label htmlFor="password">Contraseña</label>
          <br />
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="nombre-a-mostrar">Nombre a mostrar (opcional)</label>
          <br />
          <input
            id="nombre-a-mostrar"
            type="text"
            value={nombreAMostrar}
            onChange={(e) => setNombreAMostrar(e.target.value)}
            placeholder="Ej. Municipio de Prueba"
          />
        </div>
        <button type="submit" disabled={mutacion.isPending}>
          {mutacion.isPending ? "Ingresando..." : "Ingresar"}
        </button>
        {mutacion.isError && (
          <p role="alert">
            {mutacion.error instanceof ApiError
              ? mutacion.error.message
              : "No se pudo completar el ingreso. Intenta de nuevo."}
          </p>
        )}
      </form>
    </div>
  );
}

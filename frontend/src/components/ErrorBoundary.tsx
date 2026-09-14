import { Component, type ErrorInfo, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

// Red de seguridad: sin esto, un error de render en cualquier pantalla protegida
// deja la app en blanco y sin forma de recuperarse -- ProtectedLayout.tsx la
// envuelve alrededor del <Outlet/> con `key={location.pathname}`, así que navegar
// a otra ruta (incluido "atrás" del navegador) la reinicia sola en vez de quedar
// atascada en el error de la pantalla anterior.
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Error de render en una pantalla:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="mx-auto max-w-lg px-6 py-16">
          <Card>
            <CardHeader>
              <CardTitle>Esta pantalla no pudo mostrarse</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <p className="text-sm text-muted-foreground">
                Ocurrió un error inesperado al cargar esta información. El resto de la
                plataforma sigue funcionando con normalidad.
              </p>
              <Button
                onClick={() => {
                  window.location.href = "/";
                }}
              >
                Volver al inicio
              </Button>
            </CardContent>
          </Card>
        </div>
      );
    }
    return this.props.children;
  }
}

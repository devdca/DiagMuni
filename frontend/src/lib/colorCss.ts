// ECharts dibuja en <canvas>, que no entiende `var(--token)` -- esto resuelve
// la variable a su hex/rgb real al dibujar, para respetar el tema sin duplicar
// valores. Compartido por todos los componentes de ECharts.
export function resolverColorCss(valorCss: string): string {
  const variable = valorCss.match(/^var\((--[\w-]+)\)$/)?.[1];
  if (!variable) return valorCss;
  return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
}

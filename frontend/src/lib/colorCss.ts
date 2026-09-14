// ECharts dibuja en <canvas>, que no entiende `var(--token)` -- solo colores
// resueltos. Las variables de frontend/src/index.css siguen siendo la fuente de
// verdad; esto solo las resuelve a su hex/rgb real en el momento de dibujar,
// para que la gráfica respete el tema (claro/oscuro) sin duplicar ningún valor
// a mano. Compartido entre todos los componentes de ECharts del proyecto (ver
// GraficaTendenciaIndice.tsx, GraficaAvanceSeguimiento.tsx) -- antes vivía
// duplicado local a cada componente.
export function resolverColorCss(valorCss: string): string {
  const variable = valorCss.match(/^var\((--[\w-]+)\)$/)?.[1];
  if (!variable) return valorCss;
  return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
}

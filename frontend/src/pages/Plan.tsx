import { useParams } from "react-router-dom";

// Placeholder de F1 — el plan de modernización (índice actual→objetivo,
// desglose por brecha, aviso de modo degradado) es alcance de F4
// (docs/app-flow.md línea 13 y 56).
export function Plan() {
  const { tramiteId } = useParams();
  return (
    <div>
      <h2>Plan de modernización</h2>
      <p>Trámite: {tramiteId}</p>
      <p>Pantalla pendiente de construir en F4.</p>
    </div>
  );
}

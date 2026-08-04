import { useParams } from "react-router-dom";

// Placeholder de F1 — el cuestionario de captura con ramificación (F1 del
// motor, no confundir con esta tarea F1 de frontend) es alcance de F3
// (docs/app-flow.md línea 12 y 55).
export function Diagnostico() {
  const { tramiteId } = useParams();
  return (
    <div>
      <h2>Diagnóstico</h2>
      <p>Trámite: {tramiteId}</p>
      <p>Pantalla pendiente de construir en F3.</p>
    </div>
  );
}

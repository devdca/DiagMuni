import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // Mismo código con rutas relativas "/api/..." sirve en dev y en
    // producción: en producción nginx ya proxea /api al backend real
    // (nginx/nginx.conf); en dev se replica ese mismo comportamiento contra
    // el stack de Docker Compose (nginx publicado en :8090), sin variables
    // de entorno ni lógica condicional en el cliente HTTP, y sin necesidad
    // de configurar CORS en el backend.
    proxy: {
      "/api": "http://localhost:8090",
    },
  },
});

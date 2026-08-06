import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
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

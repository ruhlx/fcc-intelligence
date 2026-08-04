import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The SPA calls the FastAPI backend directly (CORS is enabled server-side).
// Override the target with VITE_API_BASE_URL at build/dev time.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  preview: { port: 4173 },
});

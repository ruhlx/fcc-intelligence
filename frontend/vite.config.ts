import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The SPA calls the FastAPI backend directly (CORS is enabled server-side).
// Override the target with VITE_API_BASE_URL at build/dev time.
//
// VITE_BASE sets the public base path: "/" for root hosting (Render static
// site), or "/<repo>/" for GitHub Pages project sites.
export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE || "/",
  server: { port: 5173 },
  preview: { port: 4173 },
});

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base = nom du repo : GitHub Pages sert le site depuis /<repo>/.
// Surchargeable (VITE_BASE=/ npm run build) si on publie un jour à la racine d'un domaine.
export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE || "/sermotheque-ebn/",
});

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/three")) {
            return "three-core";
          }

          if (
            id.includes("node_modules/@react-three") ||
            id.includes("node_modules/three-stdlib") ||
            id.includes("node_modules/@use-gesture") ||
            id.includes("node_modules/meshline")
          ) {
            return "three-react";
          }

          if (
            id.includes("node_modules/react") ||
            id.includes("node_modules/react-dom")
          ) {
            return "react-vendor";
          }

          if (
            id.includes("node_modules/framer-motion") ||
            id.includes("node_modules/react-hot-toast") ||
            id.includes("node_modules/lucide-react")
          ) {
            return "ui-vendor";
          }
        },
      },
    },
  },
});

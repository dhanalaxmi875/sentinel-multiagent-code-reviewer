import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("/node_modules/three/")) return "three-core";
          if (id.includes("/node_modules/@react-three/fiber/"))
            return "react-three-fiber";
          if (id.includes("/node_modules/@react-three/drei/"))
            return "react-three-drei";
        },
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: "localhost",
    port: 5174,
    strictPort: true,
  },
  build: {
    lib: {
      entry: "src/main.tsx", // Widget's entry point
      name: "TABWidget", // Global variable name. TODO: Not needed now. Use in future if needed
      formats: ["iife"],
      fileName: (format) => `tab-widget.${format}.js`,
    },
    rollupOptions: {
      external: [],
      output: {
        globals: {},
      },
    },
    cssCodeSplit: false, // Bundle CSS into a single file,
  },
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
});

import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const proxyTarget = process.env.VITE_PROXY_TARGET || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": { target: proxyTarget, timeout: 120000, proxyTimeout: 120000 },
      "/uploads": { target: proxyTarget, timeout: 120000, proxyTimeout: 120000 },
      "/static": { target: proxyTarget, timeout: 120000, proxyTimeout: 120000 },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
});

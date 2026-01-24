import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ["badrimicroservice.local", "localhost", "127.0.0.1"],
    port: 3000,
    strictPort: true,
    proxy: {
      "/api": {
        target:
          process.env.VITE_PROXY_TARGET ||
          process.env.VITE_ORDER_SERVICE_URL ||
          "http://localhost:5000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});

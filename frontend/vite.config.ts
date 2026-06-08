import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [react(), tailwindcss(), tsconfigPaths()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          const normalized = id.replaceAll("\\", "/");
          if (normalized.includes("/node_modules/@radix-ui/")) return "radix-ui";
          if (
            normalized.includes("/node_modules/react/") ||
            normalized.includes("/node_modules/react-dom/") ||
            normalized.includes("/node_modules/scheduler/")
          ) {
            return "react-vendor";
          }
          if (normalized.includes("/node_modules/lucide-react/")) return "icons";
          if (normalized.includes("/node_modules/recharts/") || normalized.includes("/node_modules/d3-")) return "charts";
          if (normalized.includes("/node_modules/date-fns/")) return "date-utils";
          return "vendor";
        },
      },
    },
  },
  server: {
    host: "0.0.0.0",
    port: 3000,
    strictPort: false,
    watch: {
      usePolling: true,
      interval: 250,
    },
  },
});

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    tsconfigPaths: true,
  },
  test: {
    environment: "jsdom",
    exclude: ["e2e/**", "node_modules/**"],
    pool: "forks",
    maxWorkers: 1,
    testTimeout: 30000,
    isolate: false,
    setupFiles: ["./src/test-setup.ts"],
  },
});

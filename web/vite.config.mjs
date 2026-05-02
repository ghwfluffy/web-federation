import vue from "@vitejs/plugin-vue";
import { defineConfig, loadEnv } from "vite";

function normalizeBasePath(value) {
  const trimmed = (value || "/auth").trim();
  if (trimmed === "" || trimmed === "/") {
    return "/";
  }
  return `/${trimmed.replace(/^\/+|\/+$/g, "")}/`;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const appBasePath = normalizeBasePath(env.VITE_APP_BASE_PATH);
  const apiBaseUrl = env.VITE_API_BASE_URL || `${appBasePath.replace(/\/$/, "")}/api/v1`;
  const proxyTarget = env.VITE_API_PROXY_TARGET || "http://localhost:8000";

  return {
    base: appBasePath,
    plugins: [vue()],
    server: {
      host: "0.0.0.0",
      port: 8091,
      proxy: {
        [apiBaseUrl]: {
          target: proxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(new RegExp(`^${apiBaseUrl}`), "/api/v1"),
        },
      },
    },
    test: {
      environment: "jsdom",
    },
  };
});

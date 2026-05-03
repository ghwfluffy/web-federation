import vue from "@vitejs/plugin-vue";
import { defineConfig, loadEnv } from "vite";

function normalizeBasePath(value) {
  const trimmed = value.trim();
  if (trimmed === "" || trimmed === "/") {
    return "/";
  }
  return `/${trimmed.replace(/^\/+|\/+$/g, "")}/`;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const configuredBasePath = env.VITE_APP_BASE_PATH || env.APP_BASE_PATH;
  if (configuredBasePath === undefined) {
    throw new Error("APP_BASE_PATH is required in .env.");
  }
  const appBasePath = normalizeBasePath(configuredBasePath);
  if (env.API_V1_PREFIX === undefined) {
    throw new Error("API_V1_PREFIX is required in .env.");
  }
  const apiPrefix = env.API_V1_PREFIX;
  const apiBaseUrl = env.VITE_API_BASE_URL || `${appBasePath.replace(/\/$/, "")}${apiPrefix}`;
  if (env.VITE_API_PROXY_TARGET === undefined) {
    throw new Error("VITE_API_PROXY_TARGET is required in .env.");
  }
  const proxyTarget = env.VITE_API_PROXY_TARGET;

  return {
    base: appBasePath,
    define: {
      "import.meta.env.VITE_APP_BASE_PATH": JSON.stringify(appBasePath.replace(/\/$/, "") || "/"),
      "import.meta.env.VITE_API_BASE_URL": JSON.stringify(apiBaseUrl),
      "import.meta.env.API_V1_PREFIX": JSON.stringify(apiPrefix),
    },
    plugins: [vue()],
    server: {
      host: "0.0.0.0",
      port: 8091,
      proxy: {
        [apiBaseUrl]: {
          target: proxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(new RegExp(`^${apiBaseUrl}`), apiPrefix),
        },
      },
    },
    test: {
      environment: "jsdom",
    },
  };
});

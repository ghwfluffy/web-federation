import { createRouter, createWebHistory } from "vue-router";

function normalizeAppBasePath(value: string | undefined): string {
  const trimmed = (value ?? "/auth").trim();
  if (trimmed === "" || trimmed === "/") {
    return "/";
  }
  return `/${trimmed.replace(/^\/+|\/+$/g, "")}`;
}

const appBasePath = normalizeAppBasePath(import.meta.env.VITE_APP_BASE_PATH);

export const router = createRouter({
  history: createWebHistory(appBasePath),
  routes: [
    {
      path: "/",
      component: () => import("../views/HomeView.vue"),
    },
  ],
});

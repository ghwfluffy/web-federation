import { createRouter, createWebHistory } from "vue-router";

const appBasePath = import.meta.env.VITE_APP_BASE_PATH ?? "/auth";

export const router = createRouter({
  history: createWebHistory(appBasePath),
  routes: [
    {
      path: "/",
      component: () => import("../views/HomeView.vue"),
    },
  ],
});

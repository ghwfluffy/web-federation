import "primeicons/primeicons.css";
import "./style.css";

import Aura from "@primeuix/themes/aura";
import PrimeVue from "primevue/config";
import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "./App.vue";
import { router } from "./router";

createApp(App)
  .use(createPinia())
  .use(router)
  .use(PrimeVue, {
    theme: {
      preset: Aura,
      options: {
        darkModeSelector: ".app-dark",
      },
    },
  })
  .mount("#app");

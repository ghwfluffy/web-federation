import { defineStore } from "pinia";

import { fetchStatus, type StatusPayload } from "../lib/api";

interface StatusState {
  status: StatusPayload | null;
  error: string | null;
  loading: boolean;
}

export const useStatusStore = defineStore("status", {
  state: (): StatusState => ({
    status: null,
    error: null,
    loading: false,
  }),
  actions: {
    async loadStatus(): Promise<void> {
      this.loading = true;
      this.error = null;
      try {
        this.status = await fetchStatus();
      } catch (error) {
        this.error = error instanceof Error ? error.message : "Unable to load status.";
      } finally {
        this.loading = false;
      }
    },
  },
});

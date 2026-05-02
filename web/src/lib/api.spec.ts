import { describe, expect, it, vi } from "vitest";

import { fetchStatus } from "./api";

describe("api client", () => {
  it("loads status payloads", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          status: "ok",
          app_name: "Central Auth",
          app_version: "0.1.0",
          app_base_path: "/auth",
          database: "ok",
        }),
      })),
    );

    await expect(fetchStatus()).resolves.toMatchObject({
      app_name: "Central Auth",
      app_base_path: "/auth",
    });
  });
});

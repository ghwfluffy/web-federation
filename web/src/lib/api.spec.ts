import { describe, expect, it, vi } from "vitest";

import { ApiError, fetchStatus, requestJson } from "./api";

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

  it("uses API error envelope messages", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 401,
        json: async () => ({
          error: {
            code: "http_401",
            message: "Not authenticated.",
            field_errors: [],
            request_id: "request-1",
          },
        }),
      })),
    );

    await expect(requestJson("/auth/me")).rejects.toMatchObject({
      name: "ApiError",
      message: "Not authenticated.",
      status: 401,
      code: "http_401",
      requestId: "request-1",
    } satisfies Partial<ApiError>);
  });
});

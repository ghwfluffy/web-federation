export interface StatusPayload {
  status: "ok" | "degraded";
  app_name: string;
  app_version: string;
  app_base_path: string;
  database: "ok" | "unavailable";
}

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/auth/api/v1";
export const apiBaseUrl = configuredApiBaseUrl.replace(/\/+$/, "");

export async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`, {
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export function fetchStatus(): Promise<StatusPayload> {
  return requestJson<StatusPayload>("/status");
}

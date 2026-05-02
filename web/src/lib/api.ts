export interface StatusPayload {
  status: "ok" | "degraded";
  app_name: string;
  app_version: string;
  app_base_path: string;
  database: "ok" | "unavailable";
}

export interface UserSummary {
  id: string;
  username: string;
  display_name: string | null;
  timezone: string;
  is_admin: boolean;
  is_disabled: boolean;
  avatar_url: string | null;
}

export interface SessionPayload {
  user: UserSummary;
}

export interface UserListPayload {
  users: UserSummary[];
}

export interface RegistrationCodeSummary {
  id: string;
  code: string | null;
  description: string | null;
  expires_at: string;
  revoked_at: string | null;
  created_at: string;
  created_by_user_id: string | null;
}

export interface RegistrationCodeListPayload {
  registration_codes: RegistrationCodeSummary[];
}

export interface DirectorySiteSummary {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  base_url: string;
  icon: string | null;
  required_role: string | null;
  is_enabled: boolean;
  display_order: number;
}

export interface DirectorySiteListPayload {
  sites: DirectorySiteSummary[];
}

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/auth/api/v1";
export const apiBaseUrl = configuredApiBaseUrl.replace(/\/+$/, "");

interface RequestOptions {
  method?: string;
  body?: BodyInit;
  headers?: HeadersInit;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`, {
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...options.headers,
    },
    method: options.method,
    body: options.body,
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function requestJson<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function postJson<T>(path: string, payload: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
  });
}

export function patchJson<T>(path: string, payload: unknown): Promise<T> {
  return request<T>(path, {
    method: "PATCH",
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
  });
}

export async function deleteRequest(path: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`, {
    credentials: "include",
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
}

export async function uploadAvatar(file: File): Promise<UserSummary> {
  const formData = new FormData();
  formData.append("avatar", file);
  return request<UserSummary>("/users/me/avatar", {
    method: "POST",
    body: formData,
  });
}

export function fetchStatus(): Promise<StatusPayload> {
  return requestJson<StatusPayload>("/status");
}

export function fetchMe(): Promise<SessionPayload> {
  return requestJson<SessionPayload>("/auth/me");
}

export function fetchBootstrapStatus(): Promise<{ bootstrap_required: boolean }> {
  return requestJson<{ bootstrap_required: boolean }>("/auth/bootstrap-status");
}

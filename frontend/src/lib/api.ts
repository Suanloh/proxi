import "server-only";

import { cookies } from "next/headers";

export const ownerCookie = "proxi-owner";

function apiUrl(path: string): URL {
  const base = new URL(process.env.PROXI_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1");
  if (!["http:", "https:"].includes(base.protocol) || base.username || base.password || base.search || base.hash) {
    throw new Error("PROXI_API_BASE_URL must be an HTTP(S) base URL without credentials, query, or fragment");
  }
  const [pathname, search] = path.split("?", 2);
  base.pathname = `${base.pathname.replace(/\/+$/, "")}/${pathname}`;
  if (search) base.search = search;
  return base;
}

export class ApiError extends Error {
  constructor(readonly status: number) {
    super(`Backend returned HTTP ${status}`);
  }
}

export async function api<T>(path: string, options: {method?: "POST" | "PATCH"; body?: unknown; token?: string} = {}): Promise<T> {
  const token = options.token ?? (await cookies()).get(ownerCookie)?.value;
  if (!token) throw new ApiError(401);
  const headers = new Headers({ Accept: "application/json", Authorization: `Bearer ${token}` });
  if (options.body !== undefined) headers.set("Content-Type", "application/json");
  const response = await fetch(apiUrl(path), {
    method: options.method,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    headers,
    cache: "no-store",
    redirect: "error",
    signal: AbortSignal.timeout(8000),
  });
  if (!response.ok) throw new ApiError(response.status);
  return (response.status === 204 ? undefined : await response.json()) as T;
}

export function apiMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "The backend could not be reached or returned an invalid response.";
  switch (error.status) {
    case 401: return "Owner access was not accepted. Sign in with the configured owner token.";
    case 403: return "The backend denied access for this owner.";
    case 404: return "This record was not found or is outside the owner scope.";
    case 409: return "The backend rejected the operation in its current state. Refresh and review the latest state.";
    case 422: return "The backend rejected the submitted values. Check the fields and try again.";
    default: return `The backend could not complete the request (HTTP ${error.status}).`;
  }
}

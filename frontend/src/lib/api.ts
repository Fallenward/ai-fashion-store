import type { User } from "@/lib/types";

const AUTH_KEY = "atelier-auth";
const CART_KEY = "atelier-cart";
const GUEST_KEY = "atelier-guest";

export type Session = { accessToken: string; refreshToken: string; user: User };

export function loadSession(): Session | null {
  const raw = localStorage.getItem(AUTH_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    return null;
  }
}

export function saveSession(session: Session | null) {
  if (!session) localStorage.removeItem(AUTH_KEY);
  else localStorage.setItem(AUTH_KEY, JSON.stringify(session));
  window.dispatchEvent(new Event("atelier-auth"));
}

export function storageToken(key: string) {
  let value = localStorage.getItem(key);
  if (!value) {
    value = crypto.randomUUID();
    localStorage.setItem(key, value);
  }
  return value;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function detailMessage(body: unknown, status: number) {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((item) => (typeof item === "object" && item && "msg" in item ? String((item as { msg: string }).msg) : String(item))).join(" ");
  }
  return `Request failed (${status})`;
}

async function raw(path: string, options: RequestInit = {}, retry = true): Promise<Response> {
  const headers = new Headers(options.headers);
  const session = loadSession();
  if (session?.accessToken) headers.set("Authorization", `Bearer ${session.accessToken}`);
  headers.set("X-Cart-Token", storageToken(CART_KEY));
  headers.set("X-Guest-Token", storageToken(GUEST_KEY));
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...options, headers });
  if (response.status === 401 && retry && session?.refreshToken && !path.startsWith("/api/auth/")) {
    const refreshed = await fetch("/api/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: session.refreshToken }),
    });
    if (refreshed.ok) {
      const next = (await refreshed.json()) as { access_token: string; refresh_token: string; user: User };
      saveSession({ accessToken: next.access_token, refreshToken: next.refresh_token, user: next.user });
      return raw(path, options, false);
    }
    saveSession(null);
  }
  return response;
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await raw(path, options);
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(response.status, detailMessage(body, response.status));
  return body as T;
}

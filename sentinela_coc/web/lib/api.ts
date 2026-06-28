// Cliente del Gateway COC. Bearer + refresh rotativo automático + envoltura {data, meta}.
import { clearTokens, getTokens, setTokens, type Tokens } from "./auth";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "https://api.sentinela.mx";

export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(status: number, message: string, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function refreshTokens(): Promise<boolean> {
  const t = getTokens();
  if (!t?.refresh_token) return false;
  try {
    const r = await fetch(`${API_BASE}/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: t.refresh_token }),
    });
    if (!r.ok) return false;
    setTokens((await r.json()) as Tokens);
    return true;
  } catch {
    return false;
  }
}

// ÚNICO flujo de recuperación de sesión: ante un 401 sin refresh válido, navegación DURA a
// /login?expired=1. El cambio de página cancela peticiones en vuelo y descarta la caché en
// memoria; el Login muestra el aviso de expiración. Guard anti-bucle si ya estamos en /login.
// Bandera global: aunque varias llamadas reciban 401 a la vez (o se dispare desde otra pestaña),
// se garantiza UNA sola transición -> un solo window.location.assign().
let isRedirectingToLogin = false;

export function redirectToLogin(): boolean {
  if (typeof window === "undefined") return false;
  if (isRedirectingToLogin) return true;
  if (window.location.pathname.startsWith("/login")) return false;
  isRedirectingToLogin = true;
  window.location.assign("/login?expired=1");
  return true;
}

async function request(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const t = getTokens();
  const headers = new Headers(init.headers || {});
  if (t?.access_token) headers.set("Authorization", `Bearer ${t.access_token}`);
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (res.status === 401 && retry) {
    if (await refreshTokens()) return request(path, init, false);
    clearTokens();
    // Promesa que nunca resuelve mientras la página navega -> el consumidor NO renderiza
    // pantalla de error; se queda en carga hasta cambiar a /login (transición directa).
    if (redirectToLogin()) return new Promise<Response>(() => {});
  }
  return res;
}

async function toError(res: Response): Promise<ApiError> {
  let detail = res.statusText;
  try {
    const j = await res.json();
    detail = j?.detail || j?.title || detail;
  } catch {
    /* sin cuerpo */
  }
  return new ApiError(res.status, detail);
}

function unwrap<T>(body: unknown): T {
  if (body && typeof body === "object" && "data" in (body as Record<string, unknown>)) {
    return (body as { data: T }).data;
  }
  return body as T;
}

export async function apiGet<T = unknown>(path: string): Promise<T> {
  const res = await request(path);
  if (!res.ok) throw await toError(res);
  return unwrap<T>(await res.json());
}

export async function apiGetEnvelope<T = unknown>(
  path: string,
): Promise<{ data: T; meta: { server_time: string; request_id: string; last_refresh?: string; cache_ttl_sec?: number } }> {
  const res = await request(path);
  if (!res.ok) throw await toError(res);
  return res.json();
}

export async function apiBlob(path: string): Promise<Blob> {
  const res = await request(path);
  if (!res.ok) throw await toError(res);
  return res.blob();
}

// Auth público (sin Bearer)
export async function apiPostPublic<T = unknown>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(res.status, data?.error || data?.detail || "error", data?.error);
  }
  return data as T;
}

export async function apiPost<T = unknown>(path: string, body?: unknown): Promise<T> {
  const res = await request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw await toError(res);
  return unwrap<T>(await res.json().catch(() => ({})));
}

// Abre un documento (PDF/XML) trayéndolo con Bearer y mostrándolo/descargándolo.
export async function openDocument(path: string, filename: string) {
  const blob = await apiBlob(path);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  if (filename) a.download = filename;
  a.target = "_blank";
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

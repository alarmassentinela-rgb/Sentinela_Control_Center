// Almacenamiento de tokens (cliente). El gateway emite access corto + refresh rotativo.
export type Tokens = {
  access_token: string;
  refresh_token: string;
  token_type?: string;
  expires_in?: number;
  session_id?: string;
};

const KEY = "coc.tokens";

export function getTokens(): Tokens | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Tokens) : null;
  } catch {
    return null;
  }
}

export function setTokens(t: Tokens) {
  if (typeof window !== "undefined") localStorage.setItem(KEY, JSON.stringify(t));
}

export function clearTokens() {
  if (typeof window !== "undefined") localStorage.removeItem(KEY);
}

export function isAuthed(): boolean {
  return !!getTokens()?.access_token;
}

// Identificador estable del dispositivo (para gestión de sesiones/dispositivos confiables).
export function getDeviceId(): string {
  if (typeof window === "undefined") return "web";
  let d = localStorage.getItem("coc.device");
  if (!d) {
    d = "web-" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem("coc.device", d);
  }
  return d;
}

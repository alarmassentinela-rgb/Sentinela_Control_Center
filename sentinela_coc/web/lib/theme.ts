import { apiGet } from "./api";
import type { Theme } from "./types";

export async function loadTheme(): Promise<Theme | null> {
  try {
    return await apiGet<Theme>("/v1/config/theme");
  } catch {
    return null;
  }
}

export function applyTheme(t: Theme | null) {
  if (typeof document === "undefined" || !t) return;
  if (t.primary_color) {
    document.documentElement.style.setProperty("--brand-primary", t.primary_color);
  }
}

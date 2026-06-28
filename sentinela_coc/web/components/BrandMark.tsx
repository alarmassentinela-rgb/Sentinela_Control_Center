"use client";
import { useEffect, useState } from "react";

import { cn } from "@/lib/cn";
import { loadTheme } from "@/lib/theme";
import type { Theme } from "@/lib/types";

// ÚNICA fuente de identidad visual del portal: el logo viene de Odoo (theme.logo_url).
// Lo usan AppHeader y Login -> un solo lugar para controlar la marca. Si cambia en Odoo,
// todo el portal (incluido el login) se actualiza automáticamente. Sin logo -> el nombre.
export function BrandMark({ size = "md", className }: { size?: "md" | "lg"; className?: string }) {
  const [theme, setTheme] = useState<Theme | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    loadTheme().then(setTheme);
  }, []);

  const appName = theme?.app_name || "Sentinela";
  const h = size === "lg" ? "h-16" : "h-10 sm:h-11";

  if (theme?.logo_url && !failed) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={theme.logo_url} alt={appName} onError={() => setFailed(true)} className={cn(h, "w-auto object-contain", className)} />;
  }
  return <span className={cn(size === "lg" ? "text-2xl" : "text-base", "font-bold text-ink", className)}>{appName}</span>;
}

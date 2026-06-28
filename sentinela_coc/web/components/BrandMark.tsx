"use client";
import { useEffect, useState } from "react";

import { cn } from "@/lib/cn";
import { loadTheme } from "@/lib/theme";
import type { Theme } from "@/lib/types";

// ÚNICA fuente de identidad visual del portal (logo + título). El logo viene de Odoo
// (theme.logo_url); el nombre y el título viven aquí. Lo usan AppHeader y Login -> un solo
// lugar para controlar la marca. Si cambia en Odoo (o aquí), todo el portal se actualiza.
const PORTAL_SUBTITLE = "Portal del Cliente";

export function BrandMark({ layout = "header", className }: { layout?: "header" | "login"; className?: string }) {
  const [theme, setTheme] = useState<Theme | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    loadTheme().then(setTheme);
  }, []);

  const appName = theme?.app_name || "Sentinela";
  const hasLogo = !!theme?.logo_url && !failed;

  const logo = hasLogo ? (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={theme!.logo_url}
      alt={appName}
      onError={() => setFailed(true)}
      className={cn("w-auto object-contain", layout === "login" ? "h-16" : "h-10 shrink-0 sm:h-11")}
    />
  ) : (
    <span className={cn("font-bold text-ink", layout === "login" ? "text-2xl" : "shrink-0 text-base")}>{appName}</span>
  );

  if (layout === "login") {
    return (
      <div className={cn("flex flex-col items-center gap-2 text-center", className)}>
        {logo}
        <span className="text-xl font-bold text-ink">{PORTAL_SUBTITLE}</span>
      </div>
    );
  }

  return (
    <div className={cn("flex min-w-0 items-center gap-2.5", className)}>
      {logo}
      <span className="truncate text-base font-bold leading-none tracking-tight text-ink sm:text-lg">{PORTAL_SUBTITLE}</span>
    </div>
  );
}

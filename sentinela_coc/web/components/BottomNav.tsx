"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

const ITEMS = [
  { href: "/dashboard", label: "Inicio", icon: "🏠" },
  { href: "/servicios", label: "Servicios", icon: "🧩" },
  { href: "/facturacion", label: "Facturación", icon: "🧾" },
  { href: "/soporte", label: "Soporte", icon: "💬", soon: true }, // sprint posterior
];

export function BottomNav() {
  const path = usePathname() || "";
  return (
    <nav className="sticky bottom-0 z-nav border-t border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-app">
        {ITEMS.map((it) => {
          const active = path.startsWith(it.href);
          const content = (
            <div
              className={cn(
                "flex flex-1 flex-col items-center gap-0.5 py-2 text-caption",
                active ? "text-brand" : "text-muted",
                it.soon && "opacity-40",
              )}
            >
              <span className="text-lg" aria-hidden>{it.icon}</span>
              <span>{it.label}</span>
            </div>
          );
          return it.soon ? (
            <div key={it.href} className="flex-1" title="Próximamente">
              {content}
            </div>
          ) : (
            <Link key={it.href} href={it.href} className="flex-1">
              {content}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

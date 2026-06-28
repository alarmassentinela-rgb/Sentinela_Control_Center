"use client";
import { useEffect, useRef, type ReactNode } from "react";

import { cn } from "@/lib/cn";

// Modal ÚNICO del Design System. Todo modal del portal (IA, Soporte, Tickets, Pagos,
// confirmaciones) debe usar este componente — sin variantes. Accesible: Escape para cerrar,
// focus-trap, enfoca al abrir y DEVUELVE el foco al cerrar, role=dialog + aria-labelledby,
// scroll-lock. No conoce el dominio: recibe open/onClose/title/children.
let dialogSeq = 0;

export function Dialog({
  open,
  onClose,
  title,
  children,
  className,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  className?: string;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useRef(`dialog-title-${++dialogSeq}`);

  useEffect(() => {
    if (!open) return;
    const prevFocus = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    const focusables = () =>
      panel
        ? Array.from(
            panel.querySelectorAll<HTMLElement>(
              'button:not([disabled]),[href],input:not([disabled]),select,textarea,[tabindex]:not([tabindex="-1"])',
            ),
          )
        : [];
    (focusables()[0] || panel)?.focus();

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key === "Tab") {
        const f = focusables();
        if (!f.length) return;
        const first = f[0];
        const last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    document.addEventListener("keydown", onKey);
    const html = document.documentElement;
    const prevOverflow = html.style.overflow;
    html.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      html.style.overflow = prevOverflow;
      prevFocus?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-modal flex items-end justify-center bg-black/40 sm:items-center" onClick={onClose}>
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId.current}
        onClick={(e) => e.stopPropagation()}
        className={cn(
          "max-h-[85vh] w-full max-w-app overflow-auto rounded-t-card bg-white p-4 outline-none sm:rounded-card",
          className,
        )}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 id={titleId.current} className="text-subtitle font-bold text-ink">
            {title}
          </h2>
          <button onClick={onClose} aria-label="Cerrar" className="focus-ring rounded-pill px-2 text-muted">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

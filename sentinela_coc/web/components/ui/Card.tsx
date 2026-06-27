import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export function Card({ className, children, onClick }: { className?: string; children: ReactNode; onClick?: () => void }) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "rounded-xl2 bg-white border border-slate-100 shadow-sm p-4",
        onClick && "cursor-pointer active:scale-[.99] transition",
        className,
      )}
    >
      {children}
    </div>
  );
}

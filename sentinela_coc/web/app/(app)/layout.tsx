"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BottomNav } from "@/components/BottomNav";
import { isAuthed } from "@/lib/auth";
import { applyTheme, loadTheme } from "@/lib/theme";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!isAuthed()) {
      router.replace("/login");
      return;
    }
    loadTheme().then(applyTheme);
    setReady(true);
  }, [router]);

  if (!ready) return null;

  return (
    <div className="app-shell">
      <main className="flex-1">{children}</main>
      <BottomNav />
    </div>
  );
}

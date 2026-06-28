"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppHeader } from "@/components/AppHeader";
import { BottomNav } from "@/components/BottomNav";
import { redirectToLogin } from "@/lib/api";
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

  // Sincronización entre pestañas: si otra pestaña cierra la sesión (se borran los tokens),
  // esta también vuelve al Login -> nunca queda una pestaña con datos y otra deslogueada.
  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === "coc.tokens" && !e.newValue) redirectToLogin();
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  if (!ready) return null;

  return (
    <div className="app-shell">
      <AppHeader />
      <main className="flex-1">{children}</main>
      <BottomNav />
    </div>
  );
}

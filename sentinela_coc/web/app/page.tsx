"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { isAuthed } from "@/lib/auth";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    router.replace(isAuthed() ? "/dashboard" : "/login");
  }, [router]);
  return null;
}

"use client";

import { useSearchParams } from "next/navigation";
import { useEffect } from "react";

export function useDemoMode() {
  const searchParams = useSearchParams();
  const fromUrl = searchParams.get("demo") === "true";
  const storedDemo =
    typeof window !== "undefined" &&
    localStorage.getItem("demo_mode") === "true";

  useEffect(() => {
    if (fromUrl) localStorage.setItem("demo_mode", "true");
  }, [fromUrl]);

  return { isDemo: fromUrl || storedDemo };
}

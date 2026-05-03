"use client";

import { useSearchParams } from "next/navigation";
import { useEffect } from "react";

export function useDemoMode() {
  const searchParams = useSearchParams();
  const fromUrl = searchParams.get("demo") === "true";

  useEffect(() => {
    if (fromUrl) localStorage.setItem("demo_mode", "true");
  }, [fromUrl]);

  const isDemo =
    fromUrl ||
    (typeof window !== "undefined" &&
      localStorage.getItem("demo_mode") === "true");

  return { isDemo };
}

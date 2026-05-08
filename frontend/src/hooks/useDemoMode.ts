"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

export function useDemoMode() {
  const searchParams = useSearchParams();
  const fromUrl = searchParams.get("demo") === "true";
  const [storedDemo, setStoredDemo] = useState(
    () => localStorage.getItem("demo_mode") === "true",
  );

  useEffect(() => {
    if (fromUrl) {
      localStorage.setItem("demo_mode", "true");
      setStoredDemo(true);
    }
  }, [fromUrl]);

  return { isDemo: fromUrl || storedDemo };
}

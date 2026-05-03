"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

export function useDemoMode() {
  const searchParams = useSearchParams();
  const [isDemo, setIsDemo] = useState(false);

  useEffect(() => {
    const fromUrl = searchParams.get("demo") === "true";
    const fromStorage =
      typeof localStorage !== "undefined" &&
      localStorage.getItem("demo_mode") === "true";

    if (fromUrl) {
      localStorage.setItem("demo_mode", "true");
      setIsDemo(true);
    } else {
      setIsDemo(fromStorage);
    }
  }, [searchParams]);

  return { isDemo };
}

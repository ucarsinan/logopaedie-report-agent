"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useSyncExternalStore } from "react";

const DEMO_KEY = "demo_mode";

function subscribe(onChange: () => void) {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

function getSnapshot() {
  return localStorage.getItem(DEMO_KEY) === "true";
}

function getServerSnapshot() {
  return false;
}

export function useDemoMode() {
  const searchParams = useSearchParams();
  const fromUrl = searchParams.get("demo") === "true";
  const storedDemo = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  useEffect(() => {
    if (fromUrl) localStorage.setItem(DEMO_KEY, "true");
  }, [fromUrl]);

  return { isDemo: fromUrl || storedDemo };
}

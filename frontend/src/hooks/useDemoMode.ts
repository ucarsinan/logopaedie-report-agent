"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useSyncExternalStore } from "react";

const DEMO_KEY = "demo_mode";

function subscribe(onChange: () => void) {
  window.addEventListener("storage", onChange);
  window.addEventListener("demo-mode-changed", onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener("demo-mode-changed", onChange);
  };
}

function getSnapshot() {
  return localStorage.getItem(DEMO_KEY) === "true";
}

function getServerSnapshot() {
  return false;
}

export function setDemoMode(value: boolean): void {
  if (value) {
    localStorage.setItem(DEMO_KEY, "true");
  } else {
    localStorage.removeItem(DEMO_KEY);
  }
  window.dispatchEvent(new Event("demo-mode-changed"));
}

export function getDemoMode(): boolean {
  if (typeof window === "undefined") return false;
  const fromUrl =
    new URLSearchParams(window.location.search).get("demo") === "true";
  return fromUrl || localStorage.getItem(DEMO_KEY) === "true";
}

export function useDemoMode() {
  const searchParams = useSearchParams();
  const fromUrl = searchParams.get("demo") === "true";
  const storedDemo = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  useEffect(() => {
    if (fromUrl) setDemoMode(true);
  }, [fromUrl]);

  return { isDemo: fromUrl || storedDemo };
}

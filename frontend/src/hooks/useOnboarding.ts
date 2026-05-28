"use client";

import { useSyncExternalStore } from "react";

const ONBOARDING_KEY = "logopaedie_onboarding_done";
const EVENT_NAME = "onboarding-changed";

function subscribe(onChange: () => void) {
  window.addEventListener("storage", onChange);
  window.addEventListener(EVENT_NAME, onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(EVENT_NAME, onChange);
  };
}

function getSnapshot() {
  return localStorage.getItem(ONBOARDING_KEY) === "true";
}

function getServerSnapshot() {
  // During SSR assume onboarding is done so the overlay does not flash
  // before hydration; the real value is read on the client.
  return true;
}

export function markOnboardingDone(): void {
  localStorage.setItem(ONBOARDING_KEY, "true");
  window.dispatchEvent(new Event(EVENT_NAME));
}

export function resetOnboarding(): void {
  localStorage.removeItem(ONBOARDING_KEY);
  window.dispatchEvent(new Event(EVENT_NAME));
}

export function useOnboarding() {
  const isDone = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  return { isDone };
}

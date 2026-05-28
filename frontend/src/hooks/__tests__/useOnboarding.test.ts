import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import {
  useOnboarding,
  markOnboardingDone,
  resetOnboarding,
} from "../useOnboarding";

const KEY = "logopaedie_onboarding_done";

describe("useOnboarding", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => localStorage.clear());

  it("returns isDone=false when localStorage is empty", () => {
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.isDone).toBe(false);
  });

  it("returns isDone=true when localStorage has the key set to 'true'", () => {
    localStorage.setItem(KEY, "true");
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.isDone).toBe(true);
  });

  it("returns isDone=false when the key holds a non-true value", () => {
    localStorage.setItem(KEY, "false");
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.isDone).toBe(false);
  });

  it("updates reactively when markOnboardingDone is called", () => {
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.isDone).toBe(false);
    act(() => markOnboardingDone());
    expect(result.current.isDone).toBe(true);
    expect(localStorage.getItem(KEY)).toBe("true");
  });

  it("updates reactively when resetOnboarding is called", () => {
    localStorage.setItem(KEY, "true");
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.isDone).toBe(true);
    act(() => resetOnboarding());
    expect(result.current.isDone).toBe(false);
    expect(localStorage.getItem(KEY)).toBeNull();
  });
});

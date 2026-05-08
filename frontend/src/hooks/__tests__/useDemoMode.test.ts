import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useDemoMode } from "../useDemoMode";

vi.mock("next/navigation", () => ({
  useSearchParams: vi.fn(),
}));

import { useSearchParams } from "next/navigation";

describe("useDemoMode", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams() as any);
  });

  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("returns isDemo=false when no demo param and no localStorage entry", () => {
    vi.mocked(useSearchParams).mockReturnValue(
      new URLSearchParams() as any
    );
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(false);
  });

  it("returns isDemo=true when URL param demo=true", () => {
    vi.mocked(useSearchParams).mockReturnValue(
      new URLSearchParams("demo=true") as any
    );
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(true);
  });

  it("returns isDemo=false when URL param demo=false", () => {
    vi.mocked(useSearchParams).mockReturnValue(
      new URLSearchParams("demo=false") as any
    );
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(false);
  });

  it("returns isDemo=true when localStorage has demo_mode=true", () => {
    localStorage.setItem("demo_mode", "true");
    vi.mocked(useSearchParams).mockReturnValue(
      new URLSearchParams() as any
    );
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(true);
  });

  it("returns isDemo=false when localStorage has demo_mode=false", () => {
    localStorage.setItem("demo_mode", "false");
    vi.mocked(useSearchParams).mockReturnValue(
      new URLSearchParams() as any
    );
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(false);
  });

  it("sets localStorage when demo URL param is true", () => {
    vi.mocked(useSearchParams).mockReturnValue(
      new URLSearchParams("demo=true") as any
    );
    renderHook(() => useDemoMode());
    expect(localStorage.getItem("demo_mode")).toBe("true");
  });

  it("does not set localStorage when demo URL param is false", () => {
    vi.mocked(useSearchParams).mockReturnValue(
      new URLSearchParams("demo=false") as any
    );
    renderHook(() => useDemoMode());
    expect(localStorage.getItem("demo_mode")).not.toBe("true");
  });

  it("returns isDemo=true when both URL param and localStorage are true", () => {
    localStorage.setItem("demo_mode", "true");
    vi.mocked(useSearchParams).mockReturnValue(
      new URLSearchParams("demo=true") as any
    );
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(true);
  });

  it("returns isDemo=true when only URL param is true", () => {
    vi.mocked(useSearchParams).mockReturnValue(
      new URLSearchParams("demo=true") as any
    );
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(true);
  });

  it("returns isDemo=true when only localStorage is true", () => {
    localStorage.setItem("demo_mode", "true");
    vi.mocked(useSearchParams).mockReturnValue(
      new URLSearchParams() as any
    );
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(true);
  });

  it("returns object with isDemo property", () => {
    const { result } = renderHook(() => useDemoMode());
    expect(result.current).toHaveProperty("isDemo");
    expect(typeof result.current.isDemo).toBe("boolean");
  });
});

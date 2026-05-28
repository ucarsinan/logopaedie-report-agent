import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDemoMode, setDemoMode, getDemoMode } from "../useDemoMode";

vi.mock("next/navigation", () => ({
  useSearchParams: vi.fn(),
}));

import { useSearchParams } from "next/navigation";

type SearchParamsMock = ReturnType<typeof useSearchParams>;

const mockParams = (search = "") =>
  new URLSearchParams(search) as unknown as SearchParamsMock;

describe("useDemoMode", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(useSearchParams).mockReturnValue(mockParams());
  });

  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("returns isDemo=false when no demo param and no localStorage entry", () => {
    vi.mocked(useSearchParams).mockReturnValue(mockParams());
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(false);
  });

  it("returns isDemo=true when URL param demo=true", () => {
    vi.mocked(useSearchParams).mockReturnValue(mockParams("demo=true"));
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(true);
  });

  it("returns isDemo=false when URL param demo=false", () => {
    vi.mocked(useSearchParams).mockReturnValue(mockParams("demo=false"));
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(false);
  });

  it("returns isDemo=true when localStorage has demo_mode=true", () => {
    localStorage.setItem("demo_mode", "true");
    vi.mocked(useSearchParams).mockReturnValue(mockParams());
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(true);
  });

  it("returns isDemo=false when localStorage has demo_mode=false", () => {
    localStorage.setItem("demo_mode", "false");
    vi.mocked(useSearchParams).mockReturnValue(mockParams());
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(false);
  });

  it("sets localStorage when demo URL param is true", () => {
    vi.mocked(useSearchParams).mockReturnValue(mockParams("demo=true"));
    renderHook(() => useDemoMode());
    expect(localStorage.getItem("demo_mode")).toBe("true");
  });

  it("does not set localStorage when demo URL param is false", () => {
    vi.mocked(useSearchParams).mockReturnValue(mockParams("demo=false"));
    renderHook(() => useDemoMode());
    expect(localStorage.getItem("demo_mode")).not.toBe("true");
  });

  it("returns isDemo=true when both URL param and localStorage are true", () => {
    localStorage.setItem("demo_mode", "true");
    vi.mocked(useSearchParams).mockReturnValue(mockParams("demo=true"));
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(true);
  });

  it("returns isDemo=true when only URL param is true", () => {
    vi.mocked(useSearchParams).mockReturnValue(mockParams("demo=true"));
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(true);
  });

  it("returns isDemo=true when only localStorage is true", () => {
    localStorage.setItem("demo_mode", "true");
    vi.mocked(useSearchParams).mockReturnValue(mockParams());
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(true);
  });

  it("returns object with isDemo property", () => {
    const { result } = renderHook(() => useDemoMode());
    expect(result.current).toHaveProperty("isDemo");
    expect(typeof result.current.isDemo).toBe("boolean");
  });
});

describe("setDemoMode", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(useSearchParams).mockReturnValue(mockParams());
  });

  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("writes 'true' to localStorage when called with true", () => {
    setDemoMode(true);
    expect(localStorage.getItem("demo_mode")).toBe("true");
  });

  it("removes the key from localStorage when called with false", () => {
    localStorage.setItem("demo_mode", "true");
    setDemoMode(false);
    expect(localStorage.getItem("demo_mode")).toBeNull();
  });

  it("dispatches a demo-mode-changed event so same-tab subscribers re-render", () => {
    const { result } = renderHook(() => useDemoMode());
    expect(result.current.isDemo).toBe(false);
    act(() => setDemoMode(true));
    expect(result.current.isDemo).toBe(true);
    act(() => setDemoMode(false));
    expect(result.current.isDemo).toBe(false);
  });
});

describe("getDemoMode", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("returns false when localStorage and URL are empty", () => {
    expect(getDemoMode()).toBe(false);
  });

  it("returns true when localStorage has demo_mode=true", () => {
    localStorage.setItem("demo_mode", "true");
    expect(getDemoMode()).toBe(true);
  });

  it("returns false when localStorage has demo_mode=false", () => {
    localStorage.setItem("demo_mode", "false");
    expect(getDemoMode()).toBe(false);
  });
});

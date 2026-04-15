import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

describe("root layout wires AuthProvider", () => {
  it("imports AuthProvider and wraps children", () => {
    const src = readFileSync(
      resolve(__dirname, "layout.tsx"),
      "utf8",
    );
    expect(src).toContain("AuthProvider");
    expect(src).toMatch(/<AuthProvider>[\s\S]*children[\s\S]*<\/AuthProvider>/);
  });
});

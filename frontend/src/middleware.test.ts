import { describe, it, expect } from "vitest";
import { NextRequest } from "next/server";
import { middleware } from "./middleware";

function makeRequest(pathname: string, cookies: Record<string, string> = {}): NextRequest {
  const url = `http://localhost:3000${pathname}`;
  const req = new NextRequest(url);
  for (const [name, value] of Object.entries(cookies)) {
    req.cookies.set(name, value);
  }
  return req;
}

describe("middleware", () => {
  it("passes public routes without cookie", () => {
    const res = middleware(makeRequest("/login"));
    expect(res.status).toBe(200); // NextResponse.next()
  });

  it("passes landing page without cookie", () => {
    const res = middleware(makeRequest("/"));
    expect(res.status).toBe(200);
  });

  it("redirects unauthenticated user from /module/report to /login", () => {
    const res = middleware(makeRequest("/module/report"));
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toContain("/login");
    expect(res.headers.get("location")).toContain("next=%2Fmodule%2Freport");
  });

  it("redirects unauthenticated user from /patienten to /login", () => {
    const res = middleware(makeRequest("/patienten"));
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toContain("/login");
  });

  it("redirects unauthenticated user from /settings/security to /login", () => {
    const res = middleware(makeRequest("/settings/security"));
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toContain("/login");
  });

  it("passes authenticated user to /module/report", () => {
    const res = middleware(makeRequest("/module/report", { user_role: "user" }));
    expect(res.status).toBe(200);
  });

  it("passes authenticated user to /patienten", () => {
    const res = middleware(makeRequest("/patienten", { user_role: "user" }));
    expect(res.status).toBe(200);
  });

  it("redirects non-admin from /admin/audit to /module/report", () => {
    const res = middleware(makeRequest("/admin/audit", { user_role: "user" }));
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toContain("/module/report");
  });

  it("passes admin to /admin/audit", () => {
    const res = middleware(makeRequest("/admin/audit", { user_role: "admin" }));
    expect(res.status).toBe(200);
  });
});

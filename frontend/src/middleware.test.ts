import { describe, it, expect } from "vitest";
import { NextRequest } from "next/server";
import { middleware } from "./middleware";

function makeReq(path: string, cookies: Record<string, string> = {}) {
  const url = new URL(`http://localhost:3000${path}`);
  const req = new NextRequest(url);
  for (const [k, v] of Object.entries(cookies)) {
    req.cookies.set(k, v);
  }
  return req;
}

describe("middleware", () => {
  it("redirects to /login when protected route has no access_token", () => {
    const res = middleware(makeReq("/reports"));
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toContain("/login?next=%2Freports");
  });

  it("redirects authenticated users away from /login to /", () => {
    const res = middleware(makeReq("/login", { access_token: "AT" }));
    expect(res.headers.get("location")).toBe("http://localhost:3000/");
  });

  it("redirects /admin/* to / when user_role != admin", () => {
    const res = middleware(
      makeReq("/admin/audit", { access_token: "AT", user_role: "user" }),
    );
    expect(res.headers.get("location")).toBe("http://localhost:3000/");
  });

  it("allows /admin/* when user_role=admin", () => {
    const res = middleware(
      makeReq("/admin/audit", { access_token: "AT", user_role: "admin" }),
    );
    expect(res.headers.get("location")).toBeNull();
  });

  it("lets anonymous users through on public pages", () => {
    const res = middleware(makeReq("/login"));
    expect(res.headers.get("location")).toBeNull();
  });
});

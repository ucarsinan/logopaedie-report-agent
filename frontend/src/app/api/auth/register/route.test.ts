import { describe, it, expect, vi, afterEach } from "vitest";
import { POST } from "./route";

describe("POST /api/auth/register Route Handler", () => {
  afterEach(() => vi.restoreAllMocks());

  it("forwards to backend and returns status", async () => {
    const spy = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ message: "Check email" }), {
        status: 201,
      }),
    );
    const req = new Request("http://localhost:3000/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email: "x@y.z", password: "pw1234567890" }),
    });
    const res = await POST(req);
    expect(res.status).toBe(201);
    expect(spy.mock.calls[0][0]).toContain("/auth/register");
  });
});

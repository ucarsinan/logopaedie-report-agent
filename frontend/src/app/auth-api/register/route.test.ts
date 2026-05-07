import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { POST } from "./route";

describe("POST /auth-api/register Route Handler", () => {
  beforeEach(() => {
    process.env.BACKEND_URL = "https://app.example.test/api";
  });

  afterEach(() => vi.restoreAllMocks());

  it("forwards to the backend service prefix without calling itself", async () => {
    const spy = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ message: "Check email" }), {
        status: 201,
      }),
    );
    const req = new Request("https://app.example.test/auth-api/register", {
      method: "POST",
      body: JSON.stringify({ email: "x@y.z", password: "pw1234567890" }),
    });
    const res = await POST(req);
    expect(res.status).toBe(201);
    expect(spy.mock.calls[0][0]).toBe(
      "https://app.example.test/api/auth/register",
    );
  });
});

import { afterEach, describe, expect, it } from "vitest";
import { backendTarget } from "./backend-proxy";

const ORIGINAL_ENV = {
  BACKEND_URL: process.env.BACKEND_URL,
  NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL,
  VERCEL: process.env.VERCEL,
};

function restoreEnv() {
  for (const [key, value] of Object.entries(ORIGINAL_ENV)) {
    if (value === undefined) {
      delete process.env[key];
    } else {
      process.env[key] = value;
    }
  }
}

function clearBackendEnv() {
  delete process.env.BACKEND_URL;
  delete process.env.NEXT_PUBLIC_BACKEND_URL;
  delete process.env.VERCEL;
}

describe("backendTarget", () => {
  afterEach(() => {
    restoreEnv();
  });

  it("defaults to the local backend outside Vercel", () => {
    clearBackendEnv();

    expect(
      backendTarget(
        new Request("http://localhost:3000/backend-api/sessions"),
        "/sessions",
      ),
    ).toBe("http://localhost:8001/sessions");
  });

  it("defaults to same-origin /api on Vercel", () => {
    clearBackendEnv();
    process.env.VERCEL = "1";

    expect(
      backendTarget(
        new Request("https://preview.example.vercel.app/backend-api/sessions"),
        "/sessions",
      ),
    ).toBe("https://preview.example.vercel.app/api/sessions");
  });

  it("prefers explicit BACKEND_URL over the Vercel default", () => {
    clearBackendEnv();
    process.env.VERCEL = "1";
    process.env.BACKEND_URL = "https://backend.example.test/api/";

    expect(
      backendTarget(
        new Request("https://preview.example.vercel.app/backend-api/sessions"),
        "/sessions",
      ),
    ).toBe("https://backend.example.test/api/sessions");
  });
});

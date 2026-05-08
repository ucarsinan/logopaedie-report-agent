const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8001";

export default async function globalSetup() {
  try {
    const res = await fetch(`${BACKEND_URL}/health`);
    if (!res.ok) return;
  } catch {
    console.warn("[E2E global-setup] Backend not reachable — skipping test user creation.");
    return;
  }

  await fetch(`${BACKEND_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: "e2e-test@playwright.local",
      password: "Playwright1234!",
    }),
  });
}

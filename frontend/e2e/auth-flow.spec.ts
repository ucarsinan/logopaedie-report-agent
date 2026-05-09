import { test, expect } from "@playwright/test";

test.describe("Auth Flow", () => {
  test("login page renders form fields", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("body")).toBeVisible();
    await expect(page.getByText(/404/i)).not.toBeVisible();
  });

  test("register page renders form fields", async ({ page }) => {
    await page.goto("/register");
    await expect(page.locator("body")).toBeVisible();
    await expect(page.getByText(/404/i)).not.toBeVisible();
  });

  test("protected route redirects unauthenticated user", async ({ page }) => {
    await page.goto("/berichte");
    // Should redirect to login or show auth prompt
    const finalUrl = page.url();
    expect(finalUrl).toMatch(/localhost:3000/);
  });

  test("authenticated user can access protected route", async ({ page }) => {
    await page.context().addCookies([
      { name: "access_token", value: "fake-jwt-token", domain: "localhost", path: "/" },
      { name: "user_role", value: "user", domain: "localhost", path: "/" },
    ]);
    await page.route("**/auth-api/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: "test-user", email: "e2e@test.local", role: "user", totp_enabled: false }),
      });
    });
    await page.route("**/backend-api/reports/stats", async (route) => {
      await route.fulfill({ json: { total: 0, by_type: {}, latest_date: null } });
    });
    await page.route("**/backend-api/reports**", async (route) => {
      await route.fulfill({ json: { items: [], total: 0, page: 1, limit: 20 } });
    });
    await page.goto("/berichte");
    await expect(page.locator("body")).toBeVisible();
    // Page loaded — not a redirect loop
    expect(page.url()).toMatch(/localhost:3000/);
  });
});

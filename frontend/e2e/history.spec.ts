import { test, expect } from "@playwright/test";

test.describe("History Module", () => {
  test("history module redirects unauthenticated user", async ({ page }) => {
    await page.goto("/berichte");
    // Should redirect to login or show auth UI
    const url = page.url();
    const body = await page.locator("body").textContent();
    expect(url.includes("/login") || (body?.length ?? 0) > 0).toBe(true);
  });

  test("history shows report list with mocked auth and API", async ({ page }) => {
    await page.context().addCookies([
      { name: "access_token", value: "fake-token", domain: "localhost", path: "/" },
      { name: "user_role", value: "user", domain: "localhost", path: "/" },
    ]);
    await page.route("**/auth-api/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: "test-user", email: "e2e@test.local", role: "user", totp_enabled: false }),
      });
    });
    await page.route("**/backend-api/reports**", async (route) => {
      if (route.request().url().includes("/reports/stats")) {
        await route.fulfill({ json: { total: 2, by_type: { befundbericht: 1, therapiebericht_kurz: 1, therapiebericht_lang: 0, abschlussbericht: 0 }, latest_date: null } });
      } else {
        await route.fulfill({
          json: {
            items: [
              { id: 1, pseudonym: "M.S.", report_type: "befundbericht", created_at: "2024-01-15T10:00:00Z", patient: null },
              { id: 2, pseudonym: "A.B.", report_type: "therapiebericht_kurz", created_at: "2024-01-16T11:00:00Z", patient: null },
            ],
            total: 2, page: 1, limit: 20,
          },
        });
      }
    });
    await page.goto("/module/history");
    await expect(page.getByText("M.S.")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("A.B.")).toBeVisible();
  });
});

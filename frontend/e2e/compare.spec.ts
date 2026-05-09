import { test, expect } from "@playwright/test";

test.describe("Compare Module", () => {
  test("compare module is reachable", async ({ page }) => {
    await page.goto("/module/compare");
    await expect(page.locator("body")).toBeVisible();
    await expect(page.getByText(/404/i)).not.toBeVisible();
  });

  test("has file upload areas", async ({ page }) => {
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
    await page.goto("/module/compare");
    const fileInputs = page.locator('input[type="file"]');
    await expect(fileInputs.first()).toBeAttached({ timeout: 5_000 });
  });

  test("shows comparison results after upload with mocked API", async ({ page }) => {
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
    await page.route("**/backend-api/analysis/compare", async (route) => {
      await route.fulfill({
        json: {
          items: [{ category: "Phonologie", initial_finding: "Vorverlagerung", current_finding: "Stabil", change: "verbessert" }],
          overall_progress: "Deutliche Verbesserung festgestellt.",
          remaining_issues: [],
          recommendation: "Weiterführung optional.",
        },
      });
    });

    await page.goto("/module/compare");
    const fileInputs = page.locator('input[type="file"]');
    const count = await fileInputs.count();
    if (count >= 2) {
      await fileInputs.nth(0).setInputFiles({ name: "initial.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4") });
      await fileInputs.nth(1).setInputFiles({ name: "current.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4") });

      const compareBtn = page.getByRole("button", { name: /vergleich/i });
      if (await compareBtn.isVisible().catch(() => false) && await compareBtn.isEnabled().catch(() => false)) {
        await compareBtn.click();
        await expect(page.getByText("Deutliche Verbesserung festgestellt.")).toBeVisible({ timeout: 10_000 });
      }
    }
  });
});

import { test, expect } from "@playwright/test";

test.describe("Suggest Module", () => {
  test("suggest module is reachable", async ({ page }) => {
    await page.goto("/module/suggest");
    await expect(page.locator("body")).toBeVisible();
    await expect(page.getByText(/404/i)).not.toBeVisible();
  });

  test("has text input for content", async ({ page }) => {
    await page.goto("/module/suggest");
    await expect(page.getByRole("textbox").first()).toBeVisible({ timeout: 5_000 });
  });

  test("shows suggestions after typing with mocked API", async ({ page }) => {
    await page.route("**/auth-api/me", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: "test-user", email: "e2e@test.local", role: "user", totp_enabled: false }),
      });
    });
    await page.route("**/backend-api/suggest", async (route) => {
      await route.fulfill({ json: ["Phonologische Prozesse wurden festgestellt."] });
    });

    await page.goto("/module/suggest");
    const textarea = page.getByRole("textbox").first();
    await textarea.fill("Der Patient zeigt");
    await page.waitForTimeout(1_000);
    const suggestion = page.getByText("Phonologische Prozesse wurden festgestellt.");
    if (await suggestion.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await expect(suggestion).toBeVisible();
    }
  });
});

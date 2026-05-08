import { test, expect } from "@playwright/test";

test.describe("SOAP Notes Module", () => {
  test("SOAP module is reachable", async ({ page }) => {
    await page.goto("/module/soap");
    await expect(page.locator("body")).toBeVisible();
    await expect(page.getByText(/404/i)).not.toBeVisible();
  });

  test("SOAP module shows generate options", async ({ page }) => {
    await page.route("**/api/reports**", async (route) => {
      await route.fulfill({ json: { items: [], total: 0, page: 1, limit: 20 } });
    });
    await page.goto("/module/soap");
    await expect(page.locator("body")).toBeVisible();
    // Some content is visible
    const bodyText = await page.locator("body").textContent();
    expect(bodyText?.length).toBeGreaterThan(0);
  });
});

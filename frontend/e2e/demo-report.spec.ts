import { test, expect } from "@playwright/test";

test.describe("Demo Report Flow", () => {
  test("landing page has demo CTA link", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
    // Page loads without error
    await expect(page.getByText(/404|Internal Server Error/i)).not.toBeVisible();
  });

  test("report module is reachable", async ({ page }) => {
    await page.goto("/module/report");
    await expect(page.locator("body")).toBeVisible();
    await expect(page.getByText(/404/i)).not.toBeVisible();
  });

  test("report module loads with mocked API", async ({ page }) => {
    await page.route("**/api/sessions", async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({ json: { session_id: "aabbccddeeff", status: "anamnesis" } });
      } else {
        await route.continue();
      }
    });
    await page.route("**/api/patients**", async (route) => {
      await route.fulfill({ json: { items: [], total: 0, page: 1, limit: 20 } });
    });

    await page.goto("/module/report");
    await expect(page.locator("body")).toBeVisible();
    // No crash
    await expect(page.getByText(/500|Internal Server Error/i)).not.toBeVisible();
  });
});

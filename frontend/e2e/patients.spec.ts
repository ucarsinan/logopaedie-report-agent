import { test, expect } from "@playwright/test";

test.describe("Patients Module", () => {
  test.beforeEach(async ({ page }) => {
    await page.context().addCookies([
      { name: "access_token", value: "fake-token", domain: "localhost", path: "/" },
      { name: "user_role", value: "user", domain: "localhost", path: "/" },
    ]);
  });

  test("patient list is reachable", async ({ page }) => {
    await page.route("**/api/patients**", async (route) => {
      await route.fulfill({ json: { items: [], total: 0, page: 1, limit: 20 } });
    });
    await page.goto("/patienten");
    await expect(page.locator("body")).toBeVisible();
    await expect(page.getByText(/404/i)).not.toBeVisible();
  });

  test("patient list shows patients", async ({ page }) => {
    await page.route("**/api/patients**", async (route) => {
      await route.fulfill({
        json: {
          items: [{ id: "uuid-1", system_id: "SYS-001", pseudonym: "M.S.", age_group: "Kind", disorder_text: "Phonologische Störung", created_at: "2024-01-01T00:00:00Z" }],
          total: 1, page: 1, limit: 20,
        },
      });
    });
    await page.goto("/patienten");
    await expect(page.getByText("M.S.")).toBeVisible({ timeout: 10_000 });
  });
});

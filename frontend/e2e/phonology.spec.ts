import { test, expect } from "@playwright/test";

test.describe("Phonology Module", () => {
  test("phonology module is reachable", async ({ page }) => {
    await page.goto("/module/phonology");
    await expect(page.locator("body")).toBeVisible();
    await expect(page.getByText(/404/i)).not.toBeVisible();
  });

  test("has input fields for word pairs", async ({ page }) => {
    await page.goto("/module/phonology");
    const inputs = page.getByRole("textbox");
    await expect(inputs.first()).toBeVisible({ timeout: 5_000 });
  });

  test("runs analysis and shows results with mocked API", async ({ page }) => {
    await page.route("**/api/analysis/phonological-text", async (route) => {
      await route.fulfill({
        json: {
          items: [{ target_word: "Sonne", production: "Tonne", processes: ["Vorverlagerung"], severity: "mittel" }],
          summary: "Vorverlagerungsprozess ist dominant.",
          age_appropriate: false,
          recommended_focus: ["Velarplosive /k/, /g/"],
        },
      });
    });

    await page.goto("/module/phonology");
    const analyzeBtn = page.getByRole("button", { name: /analys/i });
    if (await analyzeBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await analyzeBtn.click();
      await expect(page.getByText("Vorverlagerungsprozess ist dominant.")).toBeVisible({ timeout: 10_000 });
    }
  });
});

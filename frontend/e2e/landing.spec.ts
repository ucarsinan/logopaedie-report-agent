import { test, expect } from "@playwright/test";

test.describe("Landing Page", () => {
  test("renders hero section with CTA", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    // Two "Demo starten" links exist (header + hero) — check the header one
    await expect(
      page.getByRole("link", { name: "Demo starten", exact: true }).first()
    ).toBeVisible();
  });

  test("GitHub link points to correct repo", async ({ page }) => {
    await page.goto("/");
    const githubLink = page.getByRole("link", { name: /GitHub/i }).first();
    await expect(githubLink).toHaveAttribute(
      "href",
      "https://github.com/ucarsinan/logopaedie-report-agent"
    );
  });

  test("HowItWorks section is visible", async ({ page }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: /Vom Gespräch zum Bericht/i })
    ).toBeVisible();
  });

  test("FeatureHighlights section is visible", async ({ page }) => {
    await page.goto("/");
    // FeatureHighlights has no section heading; assert a stable feature card title.
    await expect(page.getByText("Phonologische Analyse").first()).toBeVisible();
  });

  test("Demo starten navigates to report module", async ({ page }) => {
    await page.goto("/");
    // Use the hero CTA (larger button with arrow prefix)
    await page
      .getByRole("link", { name: /Demo starten — ohne Login/i })
      .click();
    await expect(page).toHaveURL(/\/module\/report/);
  });
});

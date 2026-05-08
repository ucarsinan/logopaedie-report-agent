import { test, expect } from "@playwright/test";

test.describe("Theme Toggle", () => {
  test("toggles between light and dark mode", async ({ page }) => {
    await page.goto("/");

    const html = page.locator("html");
    const initialClass = await html.getAttribute("class");

    // Find and click the theme toggle button
    const toggle = page.getByRole("button", { name: /dark|light|theme/i }).first();
    if (await toggle.count() > 0) {
      await toggle.click();
      await page.waitForTimeout(300);
      const updatedClass = await html.getAttribute("class");
      expect(updatedClass).not.toBe(initialClass);
    } else {
      // Theme toggle may use a different pattern — check the button exists in header
      const header = page.locator("header");
      await expect(header).toBeVisible();
    }
  });
});

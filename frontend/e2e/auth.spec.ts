import { test, expect } from "@playwright/test";

test.describe("Auth Pages", () => {
  test("login page renders form", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /Anmelden|Login/i })).toBeVisible();
    await expect(page.getByRole("textbox", { name: /E-Mail|email/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Anmelden|Login/i })).toBeVisible();
  });

  test("register page renders form", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByRole("heading", { name: /Registrieren/i })).toBeVisible();
    await expect(page.getByRole("textbox", { name: /E-Mail|email/i })).toBeVisible();
  });

  test("login page link goes to register", async ({ page }) => {
    await page.goto("/login");
    const registerLink = page.getByRole("link", { name: /Registrieren|Konto erstellen/i });
    if (await registerLink.count() > 0) {
      await registerLink.click();
      await expect(page).toHaveURL(/\/register/);
    }
  });

  test("protected route redirects to login", async ({ page }) => {
    await page.goto("/berichte");
    await expect(page).toHaveURL(/\/login/);
  });
});

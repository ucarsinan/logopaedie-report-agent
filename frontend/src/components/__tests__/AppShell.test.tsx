import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/module/report",
}));

vi.mock("@/components/ThemeToggle", () => ({
  ThemeToggle: () => <div data-testid="theme-toggle" />,
}));
vi.mock("@/components/BrandLogo", () => ({
  BrandLogo: () => <span>Brand</span>,
}));
vi.mock("@/components/DemoBanner", () => ({
  DemoBanner: () => null,
}));
vi.mock("@/components/BurgerButton", () => ({
  BurgerButton: () => <button type="button">Burger</button>,
}));
vi.mock("@/components/MobileSidebar", () => ({
  MobileSidebar: () => null,
}));
vi.mock("@/features/auth/components/UserAccountBar", () => ({
  UserAccountBar: () => <div>Account</div>,
}));
vi.mock("@/hooks/useMobileNav", () => ({
  useMobileNav: () => ({ isOpen: false, toggle: vi.fn(), close: vi.fn() }),
}));

import { AppShell } from "../AppShell";

describe("AppShell skip-link", () => {
  it("renders a screen-reader-only skip link as the first focusable element", () => {
    render(
      <AppShell>
        <p>Hauptinhalt</p>
      </AppShell>,
    );

    const skipLink = screen.getByRole("link", { name: /zum hauptinhalt springen/i });
    expect(skipLink).toBeInTheDocument();
    expect(skipLink).toHaveAttribute("href", "#main-content");
    // Hidden visually by default via sr-only.
    expect(skipLink.className).toMatch(/\bsr-only\b/);
    // Becomes visible when focused.
    expect(skipLink.className).toMatch(/focus-visible:not-sr-only/);
  });

  it("targets a <main> element with id=\"main-content\"", () => {
    render(
      <AppShell>
        <p>Hauptinhalt</p>
      </AppShell>,
    );

    const main = screen.getByRole("main");
    expect(main).toHaveAttribute("id", "main-content");
  });
});

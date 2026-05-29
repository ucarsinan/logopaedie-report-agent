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

import { MobileSidebar } from "../MobileSidebar";

describe("MobileSidebar", () => {
  it("marks the active module link with aria-current=page", () => {
    render(<MobileSidebar isOpen activeSlug="phonology" onClose={vi.fn()} />);

    const activeLink = screen.getByRole("link", { name: /Ausspracheanalyse/i });
    expect(activeLink).toHaveAttribute("aria-current", "page");
  });

  it("does not set aria-current on inactive links", () => {
    render(<MobileSidebar isOpen activeSlug="phonology" onClose={vi.fn()} />);

    const inactive = screen.getByRole("link", { name: /Berichterstellung/i });
    expect(inactive).not.toHaveAttribute("aria-current");

    const patienten = screen.getByRole("link", { name: /Patienten/i });
    expect(patienten).not.toHaveAttribute("aria-current");
  });

  it("marks the Patienten link with aria-current when active", () => {
    render(<MobileSidebar isOpen activeSlug="patienten" onClose={vi.fn()} />);

    const patienten = screen.getByRole("link", { name: /Patienten/i });
    expect(patienten).toHaveAttribute("aria-current", "page");
  });
});

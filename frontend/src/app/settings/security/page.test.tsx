import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import SecurityPage from "./page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
}));

vi.mock("@/features/auth/hooks/useAuth", () => ({
  useAuth: () => ({
    state: { status: "authenticated", user: { role: "user" } },
  }),
}));

describe("SecurityPage", () => {
  it("renders password, 2fa, and sessions section headings", () => {
    render(<SecurityPage />);
    expect(
      screen.getByRole("heading", { name: /passwort ändern/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /zwei-faktor/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /aktive sitzungen/i }),
    ).toBeInTheDocument();
  });
});

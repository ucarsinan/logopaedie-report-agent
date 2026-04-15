import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SecurityPage from "./page";

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

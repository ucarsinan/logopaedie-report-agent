import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import AuthLayout from "./layout";

describe("(auth) layout", () => {
  it("renders children inside a centered card wrapper", () => {
    render(
      <AuthLayout>
        <div data-testid="child">hello</div>
      </AuthLayout>,
    );
    expect(screen.getByTestId("child")).toBeInTheDocument();
    const card = screen.getByTestId("auth-card");
    expect(card).toBeInTheDocument();
  });
});

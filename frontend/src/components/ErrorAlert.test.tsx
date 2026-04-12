import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ErrorAlert } from "./ErrorAlert";

describe("ErrorAlert", () => {
  it("renders the error message", () => {
    render(<ErrorAlert message="Something went wrong" />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("has alert role for accessibility", () => {
    render(<ErrorAlert message="Test error" />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});

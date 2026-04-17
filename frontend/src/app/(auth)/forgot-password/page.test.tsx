import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ForgotPasswordPage from "./page";

describe("ForgotPasswordPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows generic success after submit regardless of email", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ message: "ok" }), { status: 200 }),
    );
    render(<ForgotPasswordPage />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "any@x.z" },
    });
    fireEvent.click(screen.getByRole("button", { name: /senden/i }));
    await waitFor(() =>
      expect(screen.getByText(/wenn.*konto.*existiert/i)).toBeInTheDocument(),
    );
  });
});

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { RegisterForm } from "./RegisterForm";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

describe("RegisterForm", () => {
  afterEach(() => vi.restoreAllMocks());

  it("blocks submit when password < 12 chars", () => {
    render(<RegisterForm />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "a@b.c" },
    });
    fireEvent.change(screen.getByLabelText(/passwort/i), {
      target: { value: "short" },
    });
    const btn = screen.getByRole("button", { name: /registrieren/i });
    expect(btn).toBeDisabled();
  });

  it("allows submit at exactly 12 chars even if weak", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ message: "Check email" }), { status: 201 }),
    );
    render(<RegisterForm />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "a@b.c" },
    });
    fireEvent.change(screen.getByLabelText(/passwort/i), {
      target: { value: "aaaaaaaaaaaa" },
    });
    const btn = screen.getByRole("button", { name: /registrieren/i });
    expect(btn).not.toBeDisabled();
  });

  it("shows zxcvbn score progressbar", () => {
    render(<RegisterForm />);
    fireEvent.change(screen.getByLabelText(/passwort/i), {
      target: { value: "correct horse battery staple" },
    });
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("shows check-email message after successful submit", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ message: "ok" }), { status: 201 }),
    );
    render(<RegisterForm />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "a@b.c" },
    });
    fireEvent.change(screen.getByLabelText(/passwort/i), {
      target: { value: "pw1234567890ab" },
    });
    fireEvent.click(screen.getByRole("button", { name: /registrieren/i }));
    await waitFor(() =>
      expect(screen.getByText(/email.*bestätig/i)).toBeInTheDocument(),
    );
  });
});

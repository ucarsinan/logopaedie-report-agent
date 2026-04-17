import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { LoginForm } from "./LoginForm";

function mockFetch(fn: (url: string, init?: RequestInit) => Response) {
  return vi
    .spyOn(global, "fetch")
    .mockImplementation(async (url, init) =>
      fn(typeof url === "string" ? url : url.toString(), init),
    );
}

describe("LoginForm", () => {
  beforeEach(() => {
    Object.defineProperty(window, "location", {
      value: { href: "" },
      writable: true,
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it("submits credentials and redirects on success", async () => {
    mockFetch((url) => {
      if (url.endsWith("/api/auth/login"))
        return new Response(
          JSON.stringify({
            user: {
              id: "u1",
              email: "a@b.c",
              role: "user",
              totp_enabled: false,
              created_at: "",
            },
          }),
          { status: 200 },
        );
      return new Response("", { status: 404 });
    });

    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "a@b.c" },
    });
    fireEvent.change(screen.getByLabelText(/passwort/i), {
      target: { value: "pw1234567890" },
    });
    fireEvent.click(screen.getByRole("button", { name: /anmelden/i }));

    await waitFor(() => expect(window.location.href).toBe("/"));
  });

  it("shows generic error on 401", async () => {
    mockFetch(() => new Response(JSON.stringify({ detail: "x" }), { status: 401 }));
    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "a@b.c" },
    });
    fireEvent.change(screen.getByLabelText(/passwort/i), {
      target: { value: "wrongwrongwrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: /anmelden/i }));
    const err = await screen.findByRole("alert");
    expect(err.textContent).toMatch(/email.*passwort.*falsch/i);
  });

  it("renders 2FA step when backend returns 2fa_required", async () => {
    mockFetch(() =>
      new Response(
        JSON.stringify({ step: "2fa_required", challenge_id: "c1" }),
        { status: 200 },
      ),
    );
    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "a@b.c" },
    });
    fireEvent.change(screen.getByLabelText(/passwort/i), {
      target: { value: "pw1234567890" },
    });
    fireEvent.click(screen.getByRole("button", { name: /anmelden/i }));
    const twoFaInput = await screen.findByLabelText(/6-stelliger Code/i);
    expect(twoFaInput).toBeInTheDocument();
  });

  it("completes login after 2FA code submit", async () => {
    let stage = 0;
    mockFetch((url) => {
      if (url.endsWith("/api/auth/login")) {
        return new Response(
          JSON.stringify({ step: "2fa_required", challenge_id: "c1" }),
          { status: 200 },
        );
      }
      if (url.endsWith("/api/auth/login/2fa")) {
        stage = 1;
        return new Response(
          JSON.stringify({
            user: {
              id: "u1",
              email: "a@b.c",
              role: "user",
              totp_enabled: true,
              created_at: "",
            },
          }),
          { status: 200 },
        );
      }
      return new Response("", { status: 404 });
    });

    render(<LoginForm />);
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: "a@b.c" },
    });
    fireEvent.change(screen.getByLabelText(/passwort/i), {
      target: { value: "pw1234567890" },
    });
    fireEvent.click(screen.getByRole("button", { name: /anmelden/i }));

    const code = await screen.findByLabelText(/6-stelliger Code/i);
    fireEvent.change(code, { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: /bestätigen/i }));

    await waitFor(() => expect(stage).toBe(1));
  });
});

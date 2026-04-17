import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { TwoFactorSetup } from "./TwoFactorSetup";

describe("TwoFactorSetup", () => {
  afterEach(() => vi.restoreAllMocks());

  it("fetches and renders QR + secret fallback", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          secret: "JBSWY3DPEHPK3PXP",
          provisioning_uri:
            "otpauth://totp/LRA:a@b.c?secret=JBSWY3DPEHPK3PXP&issuer=LRA",
        }),
        { status: 200 },
      ),
    );
    render(<TwoFactorSetup />);
    fireEvent.click(screen.getByRole("button", { name: /2fa einrichten/i }));
    await waitFor(() =>
      expect(screen.getByText(/JBSWY3DPEHPK3PXP/)).toBeInTheDocument(),
    );
    expect(screen.getByTestId("totp-qr")).toBeInTheDocument();
  });

  it("requires 6-digit code to enable", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          secret: "X",
          provisioning_uri: "otpauth://totp/LRA:a@b.c?secret=X",
        }),
        { status: 200 },
      ),
    );
    render(<TwoFactorSetup />);
    fireEvent.click(screen.getByRole("button", { name: /2fa einrichten/i }));
    await screen.findByTestId("totp-qr");
    const btn = screen.getByRole("button", { name: /aktivieren/i });
    expect(btn).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/6-stelliger code/i), {
      target: { value: "12345" },
    });
    expect(btn).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/6-stelliger code/i), {
      target: { value: "123456" },
    });
    expect(btn).not.toBeDisabled();
  });

  it("shows success after enable", async () => {
    const spy = vi.spyOn(global, "fetch");
    spy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          secret: "X",
          provisioning_uri: "otpauth://totp/LRA:a@b.c?secret=X",
        }),
        { status: 200 },
      ),
    );
    spy.mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    render(<TwoFactorSetup />);
    fireEvent.click(screen.getByRole("button", { name: /2fa einrichten/i }));
    await screen.findByTestId("totp-qr");
    fireEvent.change(screen.getByLabelText(/6-stelliger code/i), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByRole("button", { name: /aktivieren/i }));
    await waitFor(() =>
      expect(screen.getByText(/2fa aktiviert/i)).toBeInTheDocument(),
    );
  });
});

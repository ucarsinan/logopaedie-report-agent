import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AuditLogTable } from "./AuditLogTable";

const page1 = {
  items: [
    {
      id: "a1",
      user_id: "u1",
      event: "login.success",
      ip_address: "1.2.3.4",
      user_agent: "UA",
      metadata: {},
      created_at: "2026-04-13T10:00:00Z",
    },
  ],
  total: 100,
};

describe("AuditLogTable", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders empty state when no items", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0 }), { status: 200 }),
    );
    render(<AuditLogTable />);
    await waitFor(() =>
      expect(screen.getByText(/keine einträge/i)).toBeInTheDocument(),
    );
  });

  it("filters by event", async () => {
    const spy = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify(page1), { status: 200 }),
    );
    render(<AuditLogTable />);
    await screen.findByText("login.success");
    fireEvent.change(screen.getByLabelText(/event/i), {
      target: { value: "logout" },
    });
    fireEvent.click(screen.getByRole("button", { name: /filter/i }));
    await waitFor(() => {
      const last = spy.mock.calls.at(-1);
      expect((last?.[0] as string) ?? "").toContain("event=logout");
    });
  });

  it("paginates by offset", async () => {
    const spy = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify(page1), { status: 200 }),
    );
    render(<AuditLogTable />);
    await screen.findByText("login.success");
    fireEvent.click(screen.getByRole("button", { name: /weiter/i }));
    await waitFor(() => {
      const last = spy.mock.calls.at(-1);
      expect((last?.[0] as string) ?? "").toContain("offset=50");
    });
  });
});

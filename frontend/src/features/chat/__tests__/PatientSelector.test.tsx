import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode; [key: string]: unknown }) => (
    <a href={href} {...rest}>{children}</a>
  ),
}));

vi.mock("@/lib/api", () => ({
  api: {
    patients: {
      list: vi.fn(),
    },
  },
}));

import { api } from "@/lib/api";
import { PatientSelector } from "../PatientSelector";

describe("PatientSelector", () => {
  const onSelect = vi.fn();
  const onDemo = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.patients.list).mockResolvedValue({ items: [], total: 0, page: 1, limit: 8 });
  });

  it("renders without crash", async () => {
    render(<PatientSelector onSelect={onSelect} onDemo={onDemo} />);
    expect(screen.getByText(/Patient auswählen/i)).toBeInTheDocument();
  });

  it("has a demo/start button", async () => {
    render(<PatientSelector onSelect={onSelect} onDemo={onDemo} />);
    expect(screen.getByText(/Demo-Modus/i)).toBeInTheDocument();
  });

  it("calls api.patients.list on mount", async () => {
    render(<PatientSelector onSelect={onSelect} onDemo={onDemo} />);
    await waitFor(() => {
      expect(vi.mocked(api.patients.list)).toHaveBeenCalledTimes(1);
    });
  });

  it("shows empty state when no patients found", async () => {
    vi.mocked(api.patients.list).mockResolvedValue({ items: [], total: 0, page: 1, limit: 8 });
    render(<PatientSelector onSelect={onSelect} onDemo={onDemo} />);
    await waitFor(() => {
      expect(screen.getByText(/Keine Patienten gefunden/i)).toBeInTheDocument();
    });
  });

  it("displays patients after loading", async () => {
    vi.mocked(api.patients.list).mockResolvedValue({
      items: [
        { id: "p1", pseudonym: "Max Mustermann", system_id: "SYS001", age_group: "Erwachsene" },
        { id: "p2", pseudonym: "Anna Schmidt", system_id: "SYS002", age_group: "Kinder" },
      ],
      total: 2,
      page: 1,
      limit: 8,
    } as unknown as ReturnType<typeof api.patients.list> extends Promise<infer T> ? T : never);

    render(<PatientSelector onSelect={onSelect} onDemo={onDemo} />);
    await waitFor(() => {
      expect(screen.getByText("Max Mustermann")).toBeInTheDocument();
      expect(screen.getByText("Anna Schmidt")).toBeInTheDocument();
    });
  });

  it("calls onSelect when patient is clicked", async () => {
    const patient = { id: "p1", pseudonym: "Max Mustermann", system_id: "SYS001", age_group: "Erwachsene" };
    vi.mocked(api.patients.list).mockResolvedValue({
      items: [patient],
      total: 1,
      page: 1,
      limit: 8,
    } as unknown as ReturnType<typeof api.patients.list> extends Promise<infer T> ? T : never);

    render(<PatientSelector onSelect={onSelect} onDemo={onDemo} />);
    await waitFor(() => {
      expect(screen.getByText("Max Mustermann")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Max Mustermann"));
    expect(onSelect).toHaveBeenCalledWith(patient);
  });

  it("calls onDemo when demo button is clicked", async () => {
    render(<PatientSelector onSelect={onSelect} onDemo={onDemo} />);
    fireEvent.click(screen.getByText(/Demo-Modus/i));
    expect(onDemo).toHaveBeenCalledTimes(1);
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

describe("api client", () => {
  beforeEach(() => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates sessions with optional patient_id", async () => {
    await api.sessions.create({ mode: "anamnesis", patient_id: "patient-1" });

    const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/backend-api/sessions");
    expect(call[1].method).toBe("POST");
    expect(JSON.parse(call[1].body)).toEqual({
      mode: "anamnesis",
      patient_id: "patient-1",
    });
  });

  it("keeps legacy session create signature", async () => {
    await api.sessions.create("therapy_plan");

    const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(JSON.parse(call[1].body)).toEqual({ mode: "therapy_plan" });
  });

  it("adds patient_id to reports list query", async () => {
    await api.reports.list({ patient_id: "patient-1", page: 2 });

    const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/backend-api/reports?patient_id=patient-1&page=2");
  });

  it("creates patients", async () => {
    await api.patients.create({
      realname: "Max Mustermann",
      birthdate: "2019-03-15",
      pseudonym: "Sonnenschein",
    });

    const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/backend-api/patients");
    expect(call[1].method).toBe("POST");
    expect(JSON.parse(call[1].body)).toEqual({
      realname: "Max Mustermann",
      birthdate: "2019-03-15",
      pseudonym: "Sonnenschein",
    });
  });

  it("records patient consent", async () => {
    await api.patients.consent("patient-1", "ai_processing", true);

    const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/backend-api/patients/patient-1/consent");
    expect(call[1].method).toBe("POST");
    expect(JSON.parse(call[1].body)).toEqual({
      consent_type: "ai_processing",
      granted: true,
    });
  });
});

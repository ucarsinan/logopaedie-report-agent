# Design DNA — Logopädie Report Agent

## Product Character

This product should feel like a clinical instrument, not a productivity app.
The reference category is medical documentation software — structured, precise, legible —
not SaaS landing pages or AI assistants.

Character traits in priority order:

- Precise — every label, section, and generated text reflects logopedic domain language
- Restrained — visual decisions serve structure, never attention or novelty
- Trustworthy — the output quality is the identity; the chrome disappears
- Efficient — the therapist should reach any function in two interactions

## Visual Metaphor

**The clinical workbench.** Not a chatbot. Not a dashboard. Not an onboarding flow.

Think: a well-designed medical form that also writes itself.
The layout reflects documentation structure: intake → observation → analysis → report.
The visual hierarchy follows the reading order of a logopedic report, not the hierarchy
of a marketing page.

Secondary metaphor for the landing page: **the report as proof**.
The hero is not a promise — it is a demonstration. Showing a realistic report excerpt
in the hero communicates "this is what you get" more precisely than any copywriting.

## Typography Principles

Typography carries the design. Decoration does not.

- Body and clinical content: high-legibility serif or neutral sans-serif at comfortable
  reading size (16–18px in report contexts)
- Labels and UI chrome: compact sans-serif, restrained weight contrast
- Report output sections: treated as rendered document — not chat bubbles, not cards
- No gradient text. No large display typefaces used decoratively.
- Whitespace is structural, not decorative padding

## Color Logic

- Base: near-white background, not pure white — slightly warm or cool depending on palette
- Clinical content areas: elevated off-white or subtle paper tone to signal "document"
- Primary actions: one muted, confident color — not blue-purple AI gradient
- Status indicators: functional only (error / success / in-progress) — no decorative color
- No color used as branding signal in clinical surfaces

## Design Tension

The productive tension in this product:

**Precision vs. approachability** — clinical language and structure must not feel cold
or bureaucratic. The interface should feel organized and calm, not austere.

**AI capability vs. therapist authority** — the tool generates; the therapist decides.
The UI must never present the AI output as final or authoritative. The therapist is the
expert. The tool is the instrument.

## Signature UI Elements

1. **Report preview as hero** — the live-typing demo of a realistic logopedic report
   is the primary trust-building element. It should be the most prominent thing on the
   landing page. Styled as a rendered document, not a chat interface.

2. **Session input as workbench** — the anamnese and audio input flow is structured like
   a clinical intake form with AI assistance, not like a chatbot conversation.

3. **Generated report as document** — the final report view is typeset as a document,
   with clear section headers (Befund, Diagnose, Therapieziel, Empfehlung), not as
   a response from an AI.

4. **Process indicators over feature counts** — the UI communicates where the user is
   in the documentation workflow (Aufnahme → Anamnese → Bericht), not what features
   are available.

## Avoid

- Blue-purple AI gradients or any gradient used as identity
- Decorative icons that do not carry functional meaning
- Generic SaaS section patterns (3-column feature grid, "Why us?" blocks)
- Dashboard stat cards without clinical context
- Chat bubble UI for report output
- Rounded-pill buttons as the dominant button style — prefer contained, precise shapes
- Glassmorphism or frosted-glass effects
- Any visual element that signals "AI startup" rather than "clinical tool"

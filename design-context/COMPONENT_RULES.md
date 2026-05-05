# Component Rules — Logopädie Report Agent

## Guiding Principle

Every component either serves the documentation workflow or it should not exist.
Components are not decorative. They communicate structure, state, or action within
the clinical process of session → anamnese → report.

---

## Report Preview / TypingDemo

The report preview is the highest-trust component in the entire product.

- Render output as a document, not a chat bubble or response card
- Use document-like typography: clear section headers, body text at reading size
- Section labels must use domain language: "Befund", "Diagnose", "Therapieziel",
  "Empfehlung", "Phonologische Bewusstheit" — never generic equivalents
- Typing animation (if used) should simulate clinical transcription speed, not
  the rapid "AI streaming" aesthetic
- The preview container should have a paper-like quality: subtle background, clean border,
  no SaaS card styling (no shadow-xl, no rounded-2xl)
- On the landing page: the preview is the hero. Give it the dominant visual weight.
  Do not shrink it to fit next to marketing copy.

## Session Input / Anamnese Flow

- Structured as a form, not a chat — the therapist fills in clinical observations
- Field labels use logopedic terminology (Störungsbild, Therapiephase, Behandlungsziel)
- Audio recording control: minimal, functional — record / stop / status only
- Upload areas: clearly delimited, no decorative dashed borders or cloud-upload icons
- Progress within the session flow is shown structurally (step indicator or breadcrumb),
  not with celebration states or progress bars with motivational copy

## Buttons

- Primary action: contained, confident, low-radius — matches document/form register
- Destructive actions: clearly signaled with color, never ambiguous
- No pill-shaped buttons as primary style — they read as consumer product, not clinical tool
- Icon-only buttons: only for universally understood actions (close, copy, download)
  with accessible labels; never decorative
- Loading state: subtle spinner or text replacement — no animated gradient buttons

## Cards

Cards are used only when grouping genuinely separable content.

- Report list items: structured as rows or minimal cards — show report type, date,
  patient identifier, status; no decorative elements
- Feature or capability cards on landing page: avoid unless showing real output
  or a genuine workflow step — not a feature checklist
- No "stat cards" (e.g., "42 reports generated") unless the metric has direct clinical
  or workflow meaning for the current user

## Forms

- Labels above fields, always — not placeholder-as-label
- Validation inline and specific — "Pflichtfeld" is insufficient; state what is expected
- Select fields for controlled vocabularies (Störungsbild, Berichtstyp) — not free text
- Multi-step forms: show current position in the clinical workflow, not a wizard metaphor

## Navigation

- Navigation reflects the documentation workflow: Session, Berichte, Analyse
- No sidebar nav with icon-only items unless the user is already deeply familiar
  with the product — prefer labeled nav items
- Active state: typographic weight or underline, not colored background pill
- No breadcrumb-heavy navigation in clinical views — the context should be clear
  from the content itself

## Empty States

- Session list empty: explain what the first session produces, not what the product does
  — "Noch keine Sitzung dokumentiert. Neue Sitzung starten." not "Get started with AI!"
- Report list empty: direct action, no illustration
- No decorative empty state illustrations — no waving robots, no celebration graphics
- If a process step has no output yet (e.g., report not generated), show the action
  to produce it, not a placeholder card

## Status and Feedback

- Processing states (audio transcription, report generation): progress message in
  domain language — "Transkription läuft..." / "Bericht wird erstellt..."
- Errors: specific and actionable — name what failed and what the user can do
- Success states: quiet confirmation — not toasts with checkmark animations
- Never use "AI" as a subject in status messages — "Der Bericht wurde erstellt",
  not "AI has generated your report"

## Typography in Clinical Content

- Report section headers: structured hierarchy (H2/H3), consistent weight
- Observed findings: body text, comfortable line-height for reading
- Terminology: rendered as-is — do not paraphrase or simplify logopedic terms
  in the UI (Lautdifferenzierung, Sprechapraxie, Myofunktionelle Störung)
- No inline icons mixed into clinical text

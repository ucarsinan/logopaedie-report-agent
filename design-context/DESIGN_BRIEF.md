# Design Brief — Logopädie Report Agent

## Product

A clinical documentation workspace for speech and language therapists.
The tool records therapy sessions — via audio or structured text entry — and generates
professionally formatted logopedic reports (Befundbericht, Therapiebericht, Abschlussbericht).
It is not an AI assistant. It is a documentation instrument with AI inside.

## Users

Licensed speech therapists (Logopädinnen / Logopäden) in private practice or clinical settings.
They document 6–12 patients per day. Documentation is a legal and billing obligation,
not a creative task. They are domain experts who do not need AI to explain their work —
they need AI to transcribe, structure, and render it correctly and fast.

Secondary: practice administrators reviewing or exporting finished reports.

## Context

Used at the end of a therapy session or at the end of a working day, often on a desktop
browser. The therapist is in clinical mode: focused, methodical, low tolerance for friction.
They are not in "product discovery" mode. The interface should match the pace and register
of clinical work, not SaaS onboarding.

## Emotional Target

The interface should feel:

- Calm and uncluttered — like a well-organized patient file, not a feature dashboard
- Clinically precise — the language, labels, and output must reflect logopedic terminology
- Trustworthy through evidence — the report preview is the core trust signal; it shows
  exactly what gets generated before the therapist commits
- Professionally quiet — no visual excitement, no motivational copy, no AI branding

## Primary Trust Moment

The generated report preview (TypingDemo / live output) is the single most important UI
element on the landing page. It replaces feature lists. It shows realistic clinical output
in the exact format a therapist recognizes from their own documentation practice.
A therapist who reads "Phonologische Bewusstheit: eingeschränkt — Reimwörter korrekt
identifiziert, Silbensegmentierung fehlerhaft" trusts the product. A feature card does not
create that trust.

## Must Avoid

- Generic AI SaaS aesthetics (gradients, sparkles, glassmorphism)
- Dashboard cards with no clinical meaning
- Generic marketing copy ("Supercharge your workflow", "AI-powered")
- Chatbot metaphor — this is a workbench, not a conversation
- Emoji in any clinical or professional context
- Tech-stack identity in user-facing UI (no "Powered by Groq/Llama" in primary surfaces)
- Decorative empty states
- Feature-grid sections that list capabilities instead of showing output

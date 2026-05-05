# Anti-Generic Rules — Logopädie Report Agent

These rules define what this product must not look like.
Before any UI decision, run this list as a filter.

---

## Prohibited Patterns

### AI SaaS Identity

- Blue-purple gradients as visual identity signal
- "AI sparkle" (stars, neural-net graphics, animated dots) as decoration
- "Powered by [model/provider]" in primary user-facing surfaces
- Gradient text on headlines
- Glassmorphism / frosted-glass cards as aesthetic choice
- Any visual element that reads "AI startup landing page"

### Dashboard Anti-Patterns

- Stat cards with no clinical meaning ("128 sessions analyzed", "99.2% accuracy")
- KPI grids on the main workspace view
- Activity feed or "recent actions" panels with generic icons
- Progress rings or donut charts used decoratively
- Empty dashboard with "Welcome, [name]! Here's your overview."

### Feature Marketing Patterns

- 3-column feature grid ("Fast / Accurate / Secure" or equivalent)
- "Why choose us" sections
- Testimonial carousels on product pages
- Numbered step sections explaining what the product does ("1. Record → 2. Generate → 3. Export")
  when the user is already inside the product
- Capability lists where a report preview would communicate the same information better

### Chatbot Metaphor

- Chat bubble UI for report output — reports are documents, not messages
- "Ask me anything" style input prompts
- Bot avatar or assistant persona in the clinical workspace
- "AI is thinking..." with animated typing dots for report generation
- Conversational copy in clinical contexts ("Great! Your report is ready.")

### Generic Form and Interaction Patterns

- Placeholder text used as the only label
- Generic field labels ("Name", "Notes") where clinical terms apply
  ("Patient", "Therapiephase", "Störungsbild")
- Pill-shaped primary buttons as the default style
- Success toasts with confetti or celebration animation
- Onboarding tooltips with generic product copy in a clinical session view

### Decorative Visual Patterns

- Illustration-heavy empty states (waving robots, document graphics)
- Icon + title + description blocks that exist to fill space
- Section dividers with gradient lines
- Background grid or dot patterns used as page texture
- Large hero illustrations that abstract the actual product output

---

## Anti-Generic Checkpoints

Before finalizing any page or component, verify:

1. **Does any element signal "AI startup" rather than "clinical documentation tool"?**
   If yes: remove or replace.

2. **Does any text use generic SaaS language where domain language applies?**
   ("Generate" is acceptable; "Supercharge your documentation" is not.)

3. **Is the report preview given dominant visual weight on the landing page?**
   If a feature list or illustration is visually heavier than the report preview: fix the hierarchy.

4. **Are all labels in clinical surfaces using logopedic terminology?**
   Check: session fields, report section headers, status messages.

5. **Is any component present for decoration rather than function?**
   If it does not serve a documentation workflow step: remove it.

6. **Does the empty state use domain-specific copy and a direct action?**
   If it uses generic copy or an illustration: rewrite and remove the illustration.

7. **Is "AI" mentioned as the subject of any user-facing action or status?**
   Rewrite: the product is the subject, not the AI model inside it.

---

## What Generic Looks Like vs. What This Product Looks Like

| Generic AI SaaS | This Product |
| --- | --- |
| "AI-powered reports in seconds" | A live report preview with real logopedic content |
| 3-column feature cards | The session → anamnese → report workflow shown structurally |
| Blue-purple gradient hero | Clean typeset heading + document preview |
| "Your AI assistant is ready" | "Neue Sitzung starten" |
| Dashboard with stat cards | Report list with date, type, patient, status |
| Chat bubbles for report output | Typeset document with clinical section headers |
| "Powered by Llama 3" badge | No model branding in clinical surfaces |
| Decorative empty state with illustration | "Noch keine Berichte. Erste Sitzung dokumentieren." |

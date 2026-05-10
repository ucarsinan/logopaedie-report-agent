# CODE_REVIEW.md — Review Rules & Checklist

> Use this file when reviewing a diff or a pull request.
> Agents performing a review should follow this checklist and produce output in the format below.
> Reviewers should only block on Critical issues. Non-blocking suggestions are advisory.

---

## Review Checklist

### 1. Correctness
- [ ] Does the code do what it is supposed to do?
- [ ] Are edge cases handled? (empty arrays, null/undefined, network errors, empty strings)
- [ ] Are error states surfaced to the caller or user appropriately?
- [ ] Are async/await patterns correct? Any unhandled promise rejections?
- [ ] Are race conditions possible?

### 2. Type Safety
- [ ] Are all TypeScript types correct and tight? (no unintended `any`)
- [ ] Are external inputs validated before use?
- [ ] Are return types explicit where they affect callers?
- [ ] Are nullable values handled correctly?

### 3. Architecture
- [ ] Does the change follow the patterns established in `PROJECT.md`?
- [ ] Does it violate any decisions in `DECISIONS.md`?
- [ ] Is logic placed in the right layer? (e.g., no DB access in UI components)
- [ ] Does it silently change a public API, exported type, or function signature?
- [ ] Are new abstractions justified, or could simpler code solve the problem?

### 4. Tests
- [ ] Is there test coverage for the new logic?
- [ ] Do existing tests still pass?
- [ ] Are tests testing behavior, not implementation details?
- [ ] Are edge cases covered in tests?

### 5. UI / UX (if applicable)
- [ ] Does the UI match the intended design?
- [ ] Is loading state handled?
- [ ] Is error state shown to the user?
- [ ] Does the UI work on mobile viewport?
- [ ] Are interactive elements keyboard-navigable?

### 6. Accessibility (if applicable)
- [ ] Do interactive elements have accessible labels?
- [ ] Is color contrast sufficient?
- [ ] Are ARIA attributes used correctly (not just added to silence warnings)?
- [ ] Does focus management work correctly for modals and dialogs?

### 7. Performance
- [ ] Are there any obvious N+1 query problems?
- [ ] Are large lists virtualized or paginated?
- [ ] Are expensive computations memoized where appropriate?
- [ ] Are large dependencies imported conditionally?

### 8. Security
- [ ] Is user input sanitized before use in queries or HTML?
- [ ] Are authentication and authorization checks in place?
- [ ] Are sensitive values (tokens, keys) never logged or exposed?
- [ ] Are SQL/NoSQL injections prevented?
- [ ] Are CORS and CSP headers appropriate?

### 9. Maintainability
- [ ] Is the code readable without excessive comments?
- [ ] Are identifiers named clearly?
- [ ] Is there dead code, commented-out blocks, or debug statements?
- [ ] Is the change consistent with surrounding code style?

### 10. Handoff Consistency (for AI reviews)
- [ ] Does `HANDOFF.md` accurately reflect what was changed?
- [ ] Does `CURRENT.md` reflect the actual current state?
- [ ] Are completed tasks marked done in `TASKS.md`?

---

## Review Output Format

Produce your review in this structure:

```markdown
## Code Review — [date or brief description]

**Reviewer:** [Claude Code / Codex / Gemini / human]
**Reviewed:** [file(s) or PR or diff description]

### 1. Critical Issues
<!-- Must be fixed before merge. If none: write "None." -->
- [ ] [File:line] — [description of the issue and why it matters]

### 2. Non-blocking Suggestions
<!-- Advisory improvements. Reviewer does not block on these. -->
- [ ] [File:line] — [suggestion]

### 3. Missing Tests
<!-- Test cases that should exist but don't -->
- [ ] [description of scenario that needs a test]

### 4. Risk Level
<!-- Choose one and explain why -->
**Low** | **Medium** | **High**

Reason: [brief explanation]

### 5. Recommended Next Action
[One concrete sentence: what should happen before this is merged or continued?]
```

---

## Risk Level Guide

| Level | Criteria |
|---|---|
| **Low** | Isolated change, no public API impact, good test coverage, no security concerns |
| **Medium** | Touches shared logic or multiple layers, partial test coverage, minor security considerations |
| **High** | Changes auth, data persistence, public API, or has no test coverage on critical paths |

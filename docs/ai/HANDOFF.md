# HANDOFF.md — Agent-to-Agent Handoff

> **This file enables any agent to continue work without chat history.**
> It must be updated at the end of every meaningful AI session.
> The rule: if the next agent cannot understand the situation from this file alone, the handoff is incomplete.

---

## Last Updated

- **Date:** 2026-05-10
- **Updated by:** Claude Code
- **Handoff to:** unspecified (project is stable, no active task)

---

## Short Summary

The project is stable and deployed on Vercel. All 32 Chromium e2e tests pass. CI is green. This session installed the ai-dev-workflow-template (AGENTS.md, GEMINI.md, docs/ai/, scripts/) and filled all template files with real project content. No feature work was done — this was purely a workflow infrastructure session.

---

## Last Action

Filled docs/ai/TASKS.md and docs/ai/HANDOFF.md with real content. Created AGENTS.md and GEMINI.md from .new files. Updated CLAUDE.md to import @AGENTS.md. Deleted .new files. Changes not yet committed.

---

## Changed Files

| File | Change type | Notes |
| --- | --- | --- |
| AGENTS.md | created | Renamed from AGENTS.md.new — universal AI agent rules |
| GEMINI.md | created | Renamed from GEMINI.md.new — Gemini CLI config |
| CLAUDE.md | modified | Added @AGENTS.md import at top |
| AGENTS.md.new | deleted | Replaced by AGENTS.md |
| CLAUDE.md.new | deleted | Existing CLAUDE.md is richer; .new discarded |
| GEMINI.md.new | deleted | Replaced by GEMINI.md |
| docs/ai/PROJECT.md | modified | Filled with real project info |
| docs/ai/CURRENT.md | modified | Filled with current state |
| docs/ai/TASKS.md | modified | Filled with real task board |
| docs/ai/HANDOFF.md | modified | This file |
| docs/ai/DECISIONS.md | modified | Added real project ADRs |
| scripts/ | created | 6 AI session helper scripts |

---

## Open Items

- [ ] Commit all workflow template files to git
- [ ] Fill docs/ai/DECISIONS.md with remaining project ADRs (Groq choice, Redis for sessions, etc.)
- [ ] Verify CI passes after commit

---

## Risks / Attention

- CLAUDE.md now has both project-specific content AND @AGENTS.md import. If AGENTS.md rules conflict with project CLAUDE.md rules, CLAUDE.md takes precedence (it is more specific).
- The Vercel `experimentalServices` feature used in vercel.json is beta — monitor for breaking changes.
- E2E tests only run in Chromium — Firefox/Safari not covered.

---

## Checks

| Check | Status | Notes |
| --- | --- | --- |
| `python -m pytest` | passed | 35 tests (as of 2026-05-09) |
| `npx playwright test` | passed | 32 Chromium tests (as of 2026-05-09) |
| `npm run lint` | passed | |
| `npx tsc --noEmit` | passed | |
| Manual smoke test | not done this session | No code changes made |

---

## Next Concrete Action

Commit all workflow template files: `git add AGENTS.md GEMINI.md CLAUDE.md docs/ai/ scripts/ && git commit -m "chore: install ai-dev-workflow-template and fill project state files"`. Then verify CI passes.

---

## Ideal Next Prompt

```text
Read docs/ai/HANDOFF.md, docs/ai/CURRENT.md, and docs/ai/PROJECT.md first.

Current situation: The project is stable. This session installed the ai-dev-workflow-template.
All docs/ai/ files have been filled with real content. Changes are uncommitted.

Your task: Commit all workflow template files, then pick the next task from docs/ai/TASKS.md.

After completing the task, update docs/ai/CURRENT.md, docs/ai/TASKS.md, and docs/ai/HANDOFF.md.
```

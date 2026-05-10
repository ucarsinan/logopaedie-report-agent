# GEMINI.md — Gemini CLI / Gemini Code Assist Configuration

@AGENTS.md

---

## Gemini — Specific Instructions

This file configures Gemini CLI and Gemini Code Assist for this project.
The central rule file is `AGENTS.md`. All rules defined there apply here in full.

---

## Gemini's Primary Role in This Workflow

Gemini is primarily used to **reduce premium tool usage** (Claude Code, Codex) while maintaining quality.

**Preferred tasks for Gemini:**

| Task type | Notes |
|---|---|
| Planning & breakdown | Decompose goals into concrete tasks, identify risks |
| Code analysis & review | Review diffs, check for bugs, architecture issues, security |
| Test writing | Draft unit tests, integration tests, edge case coverage |
| Documentation | Write or update docs, README sections, inline comments |
| Risk analysis | Identify fragile areas, breaking changes, missing error handling |
| Handoff consistency check | Verify that CURRENT.md, TASKS.md, HANDOFF.md are consistent and complete |
| Small/medium implementations | Self-contained features, utilities, config changes |

---

## Scope Boundaries

**Gemini should proceed autonomously with:**
- Reading all `docs/ai/` files
- Planning and analysis tasks
- Single-file changes
- Writing or improving tests
- Updating documentation files
- Updating AI context files (`CURRENT.md`, `TASKS.md`, `HANDOFF.md`)

**Gemini should ask before proceeding with:**
- Changes touching more than 3 files simultaneously
- Refactoring that alters public interfaces
- Any database schema changes
- Dependency additions or removals
- Changes to CI/CD or build configuration

**Gemini should not proceed with:**
- Destructive Git operations
- Production deployments
- Sending emails, API calls to external services
- Changes that require deep architectural understanding gained over many sessions

---

## Before Starting Work

1. Read `AGENTS.md` (full rule set).
2. Read `docs/ai/PROJECT.md` — understand the project context.
3. Read `docs/ai/CURRENT.md` — understand the active goal.
4. Read `docs/ai/HANDOFF.md` — understand what was last done.
5. State your understanding briefly before acting.

---

## During Work

- Prefer analysis and proposals over direct changes when uncertain.
- When reviewing: output issues as a structured list (see `CODE_REVIEW.md` for format).
- When planning: output a concrete task breakdown with risk notes.
- When writing tests: follow the project's existing test patterns from `PROJECT.md`.
- Do not guess at conventions — read existing code first.

---

## End of Session

Before finishing, update:

1. `docs/ai/CURRENT.md` — current status, last action, next step.
2. `docs/ai/TASKS.md` — reflect actual state of tasks.
3. `docs/ai/HANDOFF.md` — full handoff for the next agent.

The handoff must be complete enough that a fresh Claude Code or Codex session can continue without any additional context from you.

---

## What Gemini Is Best Used For in This Project

- **Planning sessions** before a Claude Code implementation sprint
- **Post-implementation review** to catch issues before merging
- **Test coverage expansion** after core features are implemented
- **Documentation passes** to keep README, API docs, and AI context files current
- **Handoff verification** to ensure the AI state files are internally consistent
- **Cost optimization** — when the task does not require deep reasoning, Gemini avoids burning Claude/Codex quota

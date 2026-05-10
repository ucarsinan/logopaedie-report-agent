# AGENTS.md — Shared AI Agent Rules

> **Central rule file for all AI agents working in this project.**
> This file applies to Claude Code, Codex, Gemini CLI, and any future AI agent.

---

## Core Principle

**The repository files are the shared truth.**

Not the chat history. Not the agent's memory. Not a previous conversation.

Every agent must be able to understand the current state and continue work **solely from the files in this repository**. If it is not written down here, it does not exist from the perspective of the next agent.

---

## Required Reading Before Any Significant Work

Before starting any non-trivial task, read the following files in order:

1. `docs/ai/PROJECT.md` — permanent project context, tech stack, conventions
2. `docs/ai/CURRENT.md` — current working state, active goal, branch
3. `docs/ai/TASKS.md` — task board: in progress, next, blocked
4. `docs/ai/DECISIONS.md` — architecture and workflow decisions (ADRs)
5. `docs/ai/HANDOFF.md` — last agent's handoff, open items, risks
6. `docs/ai/CODE_REVIEW.md` — review rules and risk criteria
7. `docs/ai/WORKFLOW.md` — daily workflow, branch rules, commit rules

For quick tasks (single-file fixes, typos, clarifications): reading `CURRENT.md` and `HANDOFF.md` is sufficient.

---

## Work Rules

### Scope

- Prefer small, focused changes over large sweeping ones.
- Do not refactor code that is not directly related to the current task.
- Do not introduce new dependencies without a written justification in `DECISIONS.md`.
- Respect the existing code style, naming conventions, and file structure.
- Do not silently change public APIs, exported types, or function signatures.

### Code Quality

- Follow TypeScript, linting, and formatting rules if they exist in the project.
- Do not remove tests. Do not skip tests to make a build pass.
- Write tests for new logic if the project has an established test pattern.
- Prefer explicit error handling. No silent catch blocks.

### Safety

- Do not output secrets, tokens, API keys, or `.env` file contents.
- Do not execute destructive Git commands (`reset --hard`, `push --force`, `branch -D`) without explicit user confirmation.
- Do not run commands that affect external services (deployments, emails, API calls) without explicit instruction.
- Ask before running any command you are uncertain about.
- When in doubt, do less and report what you found.

### Assumptions

- Do not guess at missing information. Write `TODO: needs human input` instead.
- Do not invent facts (salaries, URLs, API endpoints, credentials, dates for real entities).
- If the project context is unclear, ask before proceeding.

---

## End-of-Session Rule

At the end of every meaningful AI session, update the following files **before stopping**:

| File | What to update |
| --- | --- |
| `docs/ai/CURRENT.md` | Current goal, status, last action, next step |
| `docs/ai/TASKS.md` | Move tasks to correct columns, add new tasks |
| `docs/ai/HANDOFF.md` | Full handoff: summary, changed files, risks, next action, ideal next prompt |

The handoff must be understandable by another agent **without any chat history**.

If you ran out of context or are approaching a limit, prioritize writing `HANDOFF.md` over everything else.

---

## Agent Roles

Agents can take on different roles depending on the task. One agent can take multiple roles in a session.

| Role | Responsibility |
| --- | --- |
| **Planner** | Breaks down the goal into tasks, identifies risks, designs approach |
| **Implementer** | Writes and modifies production code |
| **Reviewer** | Reviews diffs for bugs, architecture issues, security, performance |
| **Tester** | Writes, runs, and interprets tests |
| **Documenter** | Updates docs, comments, README, and AI context files |
| **Finisher** | Cleans up, confirms all checks pass, prepares for merge |
| **Scribe** | Updates `CURRENT.md`, `TASKS.md`, `HANDOFF.md` accurately |

---

## Tool-to-Role Mapping

| Tool | Best suited for |
| --- | --- |
| **Claude Code** | Complex implementation, difficult bugs, large refactors, architecture decisions, nuanced reasoning |
| **Codex** | Implementation, test writing, code review, CLI-heavy tasks, iteration on well-defined tasks |
| **Gemini CLI** | Planning, analysis, code review, test writing, documentation, risk analysis, handoff consistency checks, smaller implementations |

**Principle:**
Use Claude Code and Codex for high-quality implementation where accuracy and reasoning depth matter.
Use Gemini to reduce premium tool usage: planning, review, documentation, test drafts, consistency checks.

---

## Codex-Specific Guidance

> Codex reads this section directly from `AGENTS.md`. There is no separate `CODEX.md` required.
> `AGENTS.md` is the canonical instruction file for Codex in this project.

### Canonical Instruction File

Codex treats `AGENTS.md` as the single source of project-wide AI rules. Do not look for a `CODEX.md` — it does not exist and is not needed.

### Required Reading Before Meaningful Work

Before starting any non-trivial task, read in order:

1. `docs/ai/PROJECT.md`
2. `docs/ai/CURRENT.md`
3. `docs/ai/TASKS.md`
4. `docs/ai/HANDOFF.md`

For quick tasks (single-file, typo fix): reading `CURRENT.md` and `HANDOFF.md` is sufficient.

### Continuing After Another Agent

When picking up from a Claude Code or Gemini session:

1. Run `git diff HEAD` to inspect uncommitted changes from the previous agent.
2. Read `HANDOFF.md` — follow the "Next Concrete Action" section.
3. Do not assume the chat history is accurate. The files are the truth.
4. If the diff contains unexpected changes, note them before proceeding.

### Reviews

When asked to perform a review:

- Enter review-only mode: do not modify any files.
- Apply the full checklist from `docs/ai/CODE_REVIEW.md`.
- Output the review in the format defined in `CODE_REVIEW.md`.
- Report: Critical Issues, Non-blocking Suggestions, Missing Tests, Risk Level, Recommended Next Action.

### Work Style

- Prefer small, focused changes over large sweeping ones.
- Do not refactor outside the scope of the current task.
- Run available checks (typecheck, lint, tests) after changes and report results.
- If a check cannot be run, state why and list what would need to be verified manually.

### End of Session

Before stopping, update:

| File | What to update |
| --- | --- |
| `docs/ai/CURRENT.md` | Current goal, status, last action, next step |
| `docs/ai/TASKS.md` | Move tasks to correct columns, add new tasks |
| `docs/ai/HANDOFF.md` | Full handoff: summary, changed files, risks, next action, ideal next prompt |

The handoff must be understandable by a fresh Claude Code or Gemini session with no chat history.

---

## Legacy AI State Handling

When both root-level AI files and `docs/ai/*` files exist in the same project:

- **Do not assume which one is current.** Both may contain valid but different snapshots of project state.
- **Prefer `docs/ai/*` only after** migration is explicitly documented in `docs/ai/HANDOFF.md`. If `docs/ai/HANDOFF.md` has no migration note, treat both sources as potentially valid.
- **Do not delete or overwrite root-level legacy files** (`HANDOFF.md`, `TASKS.md`, `DECISIONS.md`, `PROJECT_STATE.md`, etc.) unless a human explicitly instructs you to do so.
- **`.new` files are candidate template updates, not authoritative state.** A file named `AGENTS.md.new` is the generic template the installer wrote — it does not override the existing `AGENTS.md`.
- **If asked to work with AI state files and both legacy and new files exist:** read both, note any conflicts or gaps, and ask for or produce a migration plan before making changes.
- **The safe default:** report what you found in each location and ask the human which version represents current truth before modifying anything.

---

## End-of-Session Output Format

When finishing a session, produce a structured summary in this format:

```markdown
## Session Summary

**Agent:** [Claude Code | Codex | Gemini]
**Date:** YYYY-MM-DD
**Role(s):** [e.g., Implementer + Scribe]

### What was done
- ...

### Files changed
- path/to/file.ts — reason

### What is NOT done yet
- ...

### Risks / Attention
- ...

### Next concrete action
[One sentence]

### Ideal next prompt
[Ready-to-copy prompt for the next agent]
```

Then update `docs/ai/CURRENT.md`, `docs/ai/TASKS.md`, and `docs/ai/HANDOFF.md` accordingly.

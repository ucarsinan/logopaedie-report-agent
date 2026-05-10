# WORKFLOW.md — Daily AI Development Workflow

> This file describes how to work with multiple AI agents across sessions.
> Follow these rules to avoid context loss, duplicate work, and conflicting changes.

---

## Core Principle

**Start with Claude Code or Codex for implementation.**
**Delegate planning, reviews, tests, documentation, and risk analysis to Gemini.**

The goal is to use premium tools (Claude Code, Codex) for work that genuinely requires deep reasoning, and to offload everything else to Gemini to preserve quota and context budget.

The repository files are always the shared truth. A session that does not update `CURRENT.md`, `TASKS.md`, and `HANDOFF.md` before ending is an incomplete session.

**Tool adapter files:**

- `CLAUDE.md` — Claude Code reads this as its entrypoint; it imports `AGENTS.md`.
- `GEMINI.md` — Gemini reads this as its entrypoint; it imports `AGENTS.md`.
- Codex — reads `AGENTS.md` directly. No separate `CODEX.md` is needed or created.

---

## Starting a Session

1. Run `./scripts/ai-status.sh` to see the current state at a glance.
2. Use `./scripts/ai-start.sh | pbcopy` to generate a start prompt.
3. Paste the prompt into Claude Code, Codex, or Gemini.
4. The agent reads the AI state files and summarizes the situation.
5. Confirm the summary is accurate before proceeding.
6. If the summary is wrong, correct the files first before starting work.

---

## Ending a Session

1. Use `./scripts/ai-handoff-prompt.sh | pbcopy` to generate the handoff prompt.
2. Paste into the current agent.
3. The agent updates `docs/ai/CURRENT.md`, `docs/ai/TASKS.md`, `docs/ai/HANDOFF.md`.
4. Review the updates quickly to confirm accuracy.
5. Commit the AI state files:
   ```bash
   git add docs/ai/CURRENT.md docs/ai/TASKS.md docs/ai/HANDOFF.md
   git commit -m "docs(ai): update session handoff [agent: Claude Code]"
   ```

---

## Switching from Claude Code to Codex

1. End the Claude Code session: run the handoff prompt, verify files are updated.
2. Commit the updated AI state files.
3. Open Codex.
4. Use the "Ideal Next Prompt" from `docs/ai/HANDOFF.md` as the starting prompt.
5. Codex reads `HANDOFF.md`, `CURRENT.md`, `PROJECT.md` and continues.
6. Codex runs `git diff HEAD` to inspect any uncommitted changes left by the previous agent.

No manual re-explanation is needed. The files contain all context.

**Note:** There is no `CODEX.md` in this workflow. Codex reads `AGENTS.md` directly as its canonical instruction file. The `CLAUDE.md` and `GEMINI.md` adapter files exist because those tools require a specific entrypoint — Codex does not.

---

## Switching from Codex to Claude Code

Same process as above, reversed.

1. End Codex session with the handoff prompt.
2. Commit AI state files.
3. Open Claude Code.
4. Use the "Ideal Next Prompt" from `docs/ai/HANDOFF.md`.

---

## Using Gemini to Reduce Premium Tool Usage

Before starting a Claude Code or Codex session, ask: can Gemini do this?

**Send to Gemini first:**
- Planning a feature: use `PROMPTS.md > Gemini Planning Prompt`
- Reviewing a diff or PR: use `PROMPTS.md > Gemini Review Prompt`
- Writing tests for implemented code: use `PROMPTS.md > Gemini Test Prompt`
- Updating documentation: use `PROMPTS.md > Documentation Prompt`
- Verifying handoff consistency: use `PROMPTS.md > Handoff Consistency Check Prompt`
- Small/medium self-contained tasks

**Send to Claude Code / Codex:**
- Complex multi-file implementation
- Difficult bugs requiring deep reasoning
- Architecture decisions
- Security-sensitive changes
- TypeScript-heavy refactoring
- Anything where Gemini output was insufficient

---

## When to Use Which Tool

| Situation | Recommended tool |
|---|---|
| Planning a new feature | Gemini |
| Implementing a complex feature | Claude Code |
| Implementing a well-defined task | Codex |
| Writing unit tests | Gemini |
| Reviewing a PR or diff | Gemini |
| Updating documentation | Gemini |
| Difficult bug requiring reasoning | Claude Code |
| Refactoring with type-level changes | Claude Code |
| CLI scripting or automation | Codex |
| Handoff consistency check | Gemini |
| Risk analysis | Gemini |

---

## Branch Rules

- Never work directly on `main` or `master`.
- Branch naming: `feat/`, `fix/`, `refactor/`, `docs/`, `chore/` prefixes.
- Keep branches focused on one feature or fix.
- AI agents should state the current branch at the start of each session.
- If unsure which branch to use, check `docs/ai/CURRENT.md`.

---

## Commit Rules

- Follow Conventional Commits: `type(scope): description`
- Write commit messages in English.
- Keep commits small and focused.
- Always include what changed and why (briefly) in the body if non-obvious.
- AI state file commits use `docs(ai):` prefix.

```bash
# Examples
feat(auth): add email/password sign-in with Supabase
fix(login): redirect to /dashboard after successful sign-in
docs(ai): update handoff after auth implementation session
test(auth): add unit tests for session validation
```

---

## Rules for Parallel Agents

If two agents work simultaneously on the same repository:

- Each agent must work on a **different branch**.
- Agents must not edit the same AI state files at the same time.
- Designate one agent as the "Scribe" responsible for updating `CURRENT.md`, `TASKS.md`, `HANDOFF.md`.
- Merge or rebase frequently to avoid diverging state.
- After merging, run a handoff consistency check (Gemini) before starting the next session.

---

## Rules for Reviews

- All reviews follow the checklist in `docs/ai/CODE_REVIEW.md`.
- Review output follows the format defined in `CODE_REVIEW.md`.
- Critical issues block merge. Non-blocking suggestions are advisory.
- Prefer Gemini for reviews to avoid burning Claude Code context on non-implementation work.
- After a review, update `TASKS.md` with any action items identified.

---

## What to Do When a Context Limit Is Hit

1. **Before the limit is fully reached**: start a handoff immediately.
   - Run `./scripts/ai-handoff-prompt.sh | pbcopy`
   - Paste into the current agent
   - Let it update the AI state files
2. If the agent can no longer respond meaningfully: write the handoff manually in `HANDOFF.md`.
3. Commit the AI state files.
4. Open a new session with the fresh start prompt from `./scripts/ai-start.sh`.

A partial handoff is always better than no handoff. Even a short "we got to X, next step is Y" is enough.

### When the Next Agent Is Codex or Claude Code

The incoming agent must:

1. Read `docs/ai/HANDOFF.md` — the starting point for all context.
2. Read `docs/ai/CURRENT.md` and `docs/ai/TASKS.md`.
3. Run `git diff HEAD` to inspect any uncommitted changes left by the previous session.
4. Summarize the situation before touching any file.
5. Follow the "Next Concrete Action" in `HANDOFF.md`.

Do not rely on chat history from the previous session — it is not available and should not be reconstructed from memory.

---

## Existing Project With Legacy AI Files

If you installed this workflow into a project that already had root-level AI-state files
(`AGENTS.md`, `CLAUDE.md`, `HANDOFF.md`, `TASKS.md`, `DECISIONS.md`, `PROJECT_STATE.md`, etc.),
follow this sequence before starting regular development sessions.

### Step 1 — Run the installer

```bash
/path/to/ai-dev-workflow-template/scripts/install-ai-workflow.sh
```

The installer detects legacy files, reports them, and never modifies them.
New template files are written as `.new` where conflicts exist.

### Step 2 — Inspect `.new` files

```bash
find . -name "*.new" | sort
```

Each `.new` file is the fresh template version. Your existing file may contain important project-specific rules. Compare them before merging.

### Step 3 — Run the migration prompt

```bash
./scripts/ai-migrate-legacy-prompt.sh | pbcopy
```

Paste into **Gemini first** when possible. Gemini handles large reading tasks well and does not burn Claude Code quota.

The prompt instructs the agent to:

- Read all legacy root files and all new `docs/ai/` files
- Merge content following the standard migration mapping
- Leave original files untouched
- Produce a migration report

### Step 4 — Validate with Claude Code or Codex

Paste the start prompt into Claude Code:

```bash
./scripts/ai-start.sh | pbcopy
```

Ask the agent to read `docs/ai/PROJECT.md`, `docs/ai/CURRENT.md`, and `docs/ai/HANDOFF.md` and produce a project summary. If the summary is accurate, the migration is complete.

### Step 5 — Archive old root files (only after validation)

Only after a human has confirmed the migration is accurate:

```bash
mkdir -p _archive/legacy-ai-state
mv HANDOFF.md TASKS.md DECISIONS.md PROJECT_STATE.md _archive/legacy-ai-state/
# AGENTS.md, CLAUDE.md, GEMINI.md stay in the root permanently
```

See `docs/ai/LEGACY_MIGRATION.md` for the full migration guide, including the no-git workflow.

---

## What to Do When Checks Fail

1. Do NOT commit broken code.
2. Note the failure in `CURRENT.md` under "Blocked" or "Known Problems".
3. If the failure is a pre-existing issue (not caused by this session), note it and continue.
4. If the failure is caused by this session, fix it before ending.
5. If you cannot fix it, document exactly what fails and why in `HANDOFF.md`.

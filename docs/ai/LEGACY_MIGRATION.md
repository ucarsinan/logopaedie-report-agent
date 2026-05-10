# LEGACY_MIGRATION.md — Migrating Existing AI-State Files

> This file is created when the AI Dev Workflow installer detects an existing project.
> It documents the safe migration path for legacy root-level AI-state files.

---

## What Are Legacy AI-State Files?

Legacy AI-state files are Markdown files that accumulated in the project root before this workflow was installed. They may include:

- `AGENTS.md` — agent rules written for a previous setup
- `CLAUDE.md` — Claude Code configuration written manually
- `GEMINI.md` — Gemini configuration
- `HANDOFF.md` — session handoffs written in the root
- `TASKS.md` — a task list maintained in the root
- `DECISIONS.md` — architecture decisions
- `PROJECT_STATE.md` — project state snapshots
- `RESEARCH.md` — research notes
- any other Markdown files used as AI context

These files are valid, real history. They must not be blindly overwritten or deleted.

---

## Why They Must Not Be Blindly Overwritten

Legacy files often contain:

- Project-specific constraints and safety rules built up over months
- Architecture decisions that are not written anywhere else
- Current task state that is still accurate
- Custom agent instructions tailored to this project

Overwriting them with the generic template would destroy that accumulated context.

---

## Prerequisite

The `docs/ai/` template structure must be installed before running any migration.

Required files:
- `docs/ai/PROJECT.md`
- `docs/ai/CURRENT.md`
- `docs/ai/TASKS.md`
- `docs/ai/DECISIONS.md`
- `docs/ai/HANDOFF.md`

If any of these are missing, stop and run the installer first:
```bash
./scripts/install-ai-workflow.sh
```
Then return to this migration guide.

---

## Migration File Mapping

### Allowed migration targets

Content may only be migrated into these files:

| Root file | Migrate into | Notes |
|---|---|---|
| `AGENTS.md` | `AGENTS.md` (root; keep in place) | Merge project-specific rules; use `AGENTS.md.new` as structure base |
| `CLAUDE.md` | `CLAUDE.md` (root; keep in place) | Merge project-specific rules; use `CLAUDE.md.new` as structure base |
| `HANDOFF.md` | `docs/ai/HANDOFF.md` | Merge; preserve existing headings |
| `TASKS.md` | `docs/ai/TASKS.md` | Merge; append under subsection if conflict |
| `DECISIONS.md` | `docs/ai/DECISIONS.md` | Merge; append under subsection if conflict |
| `PROJECT_STATE.md` | `docs/ai/PROJECT.md` + `docs/ai/CURRENT.md` | Persistent facts → PROJECT.md; live state → CURRENT.md |
| `PROJECT.md` | `docs/ai/PROJECT.md` | Merge with stub; preserve existing headings |
| `CURRENT.md` | `docs/ai/CURRENT.md` | Merge; preserve existing headings |
| `RESEARCH.md` | `docs/ai/RESEARCH.md` (if it exists) or summarize into `docs/ai/PROJECT.md` | Keep if still relevant |
| `GEMINI.md` | `AGENTS.md` notes section | Extract unique project-specific rules only |

### Forbidden migration targets

Never create or modify these files during migration:

| Legacy source | Why it is forbidden | What to do instead |
|---|---|---|
| `CODE_REVIEW.md` | `docs/ai/CODE_REVIEW.md` is a template file — do not create | Summarize key rules into `docs/ai/DECISIONS.md` |
| `PROMPTS.md` | `docs/ai/PROMPTS.md` is a template file — do not create | Skip or note in report |
| `WORKFLOW.md` | `docs/ai/WORKFLOW.md` is a template file — do not create | Summarize key workflow rules into `docs/ai/PROJECT.md` |
| Any `*.new` file | These are installer artifacts — do not modify | Leave in place |
| Root legacy files | Do not modify legacy sources during migration | Leave in place |

Also never create or modify: `CHANGELOG.md`, `README.md`, `scripts/*`, `*.py`, `requirements.txt`, `launchagents/*`.

---

## Understanding `.new` Files

When the installer finds an existing file, it writes the template version as `filename.new` instead of overwriting.

| File | Meaning |
|---|---|
| `AGENTS.md` | Your existing version — may contain project-specific rules |
| `AGENTS.md.new` | Fresh template — generic structure from the new workflow |

The `.new` file is a **candidate**, not the truth. It contains the template structure you should adopt, but your existing file contains the content that matters for this project.

**Do not delete your `.new` files yet.** Use them as a reference during migration.

---

## Recommended Safe Migration Sequence

1. **Run the installer** (already done if you are reading this).
   Verify the required `docs/ai/` files exist before proceeding.
   If missing, run `./scripts/install-ai-workflow.sh` again.

2. **Inspect what was detected.**
   The installer printed a table of legacy files found and their suggested targets.

3. **Generate the migration prompt.**
   ```bash
   ./scripts/ai-migrate-legacy-prompt.sh | pbcopy
   ```
   The script will exit with an error if the `docs/ai/` structure is incomplete.

4. **Choose your migration tool.**

   **Preferred: Claude Code or Codex** — use for the full migration run.
   They provide the strongest multi-file reasoning and most reliable constraint adherence.

   ```bash
   # Paste into Claude Code:
   ./scripts/ai-migrate-legacy-prompt.sh | pbcopy
   ```

   **Gemini:** use only for small, phased analysis tasks — for example:
   - Summarizing a single legacy file before the main migration
   - Reviewing the migration report after Claude Code / Codex has done the writes
   - Consistency-checking `docs/ai/` files post-migration

   If you use Gemini for the full migration, review every write carefully before accepting.

5. **Review the migration report.**
   Check what was moved, what was marked TODO, and what the agent was uncertain about.
   Confirm that no forbidden files were created or modified.
   Verify `.new` file status: `find . -name "*.new" | sort`

6. **Validate with Claude Code or Codex.**
   Paste the start prompt (`./scripts/ai-start.sh | pbcopy`) into Claude Code.
   Ask it to read `docs/ai/PROJECT.md`, `docs/ai/CURRENT.md`, and `docs/ai/HANDOFF.md`.
   Confirm that the project summary it produces is accurate.

7. **Only after validation: archive old root files.**
   Move them to `_archive/legacy-ai-state/` — do not delete.
   ```bash
   mkdir -p _archive/legacy-ai-state
   mv HANDOFF.md TASKS.md DECISIONS.md _archive/legacy-ai-state/
   # Keep AGENTS.md, CLAUDE.md, GEMINI.md in root — they are still needed there.
   ```

8. **Remove `.new` files** once you have reviewed and merged their contents.

---

## If the Project Has No Git Repository

This workflow does not require git. If the project has no `.git` directory:

- Skip all git commands in the migration sequence.
- Use `cp` to manually archive legacy files instead of git mv.
- Do not commit; simply save files to their new locations.
- The `docs/ai/` files work as shared AI memory regardless of git.

---

## What to Do With Old Root Files After Verification

Once you have verified that `docs/ai/` contains accurate, complete state:

1. Archive (do not delete):
   ```bash
   mkdir -p _archive/legacy-ai-state
   mv HANDOFF.md TASKS.md DECISIONS.md PROJECT_STATE.md RESEARCH.md _archive/legacy-ai-state/
   ```

2. Do not archive `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` — they stay in the project root permanently. The new template versions should now live there (merged with your project-specific content).

3. Add `_archive/` to `.gitignore` if you do not want it version-controlled:
   ```
   _archive/
   ```

---

## How to Validate After Migration

Run the standard start prompt and ask the agent to produce a project summary:

```bash
./scripts/ai-start.sh | pbcopy
# Paste into Claude Code or Gemini
```

The agent should be able to produce:
- A correct description of the project and tech stack
- The current active goal
- A list of recent tasks and their status
- Known risks or blockers

If the summary is wrong or incomplete, the migration is not done — return to step 5.

---

## Warning

**Do not delete legacy AI-state files until:**

1. You have validated that `docs/ai/` contains the complete, accurate state.
2. At least one agent session has produced a correct project summary from `docs/ai/` alone.
3. You (a human) have reviewed the migrated files and confirmed nothing was lost.

A premature deletion of legacy files can result in permanent loss of accumulated project context.

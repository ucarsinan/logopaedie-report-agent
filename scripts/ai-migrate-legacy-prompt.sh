#!/usr/bin/env bash
# ai-migrate-legacy-prompt.sh
# Outputs a copy-paste migration prompt for Claude Code, Codex, or Gemini.
# Usage: ./scripts/ai-migrate-legacy-prompt.sh | pbcopy
#        ./scripts/ai-migrate-legacy-prompt.sh | xclip -selection clipboard

set -euo pipefail

TARGET_DIR="${1:-$(pwd)}"

# ─── Verify docs/ai/ template structure exists ──────────────────────────────

REQUIRED_DOCS_AI=(
  "docs/ai/PROJECT.md"
  "docs/ai/CURRENT.md"
  "docs/ai/TASKS.md"
  "docs/ai/DECISIONS.md"
  "docs/ai/HANDOFF.md"
)

missing_required=()
for f in "${REQUIRED_DOCS_AI[@]}"; do
  if [ ! -f "$TARGET_DIR/$f" ]; then
    missing_required+=("$f")
  fi
done

if [ ${#missing_required[@]} -gt 0 ]; then
  echo "ERROR: The docs/ai/ template structure is missing or incomplete." >&2
  echo "The following required files were not found:" >&2
  for f in "${missing_required[@]}"; do
    echo "  - $f" >&2
  done
  echo "" >&2
  echo "Run the installer first:" >&2
  echo "  ./scripts/install-ai-workflow.sh" >&2
  echo "" >&2
  echo "Then re-run this script." >&2
  exit 1
fi

# ─── Detect legacy files ────────────────────────────────────────────────────

LEGACY_FILES=(
  AGENTS.md
  CLAUDE.md
  GEMINI.md
  HANDOFF.md
  TASKS.md
  DECISIONS.md
  PROJECT_STATE.md
  PROJECT.md
  CURRENT.md
  RESEARCH.md
  CODE_REVIEW.md
  PROMPTS.md
  WORKFLOW.md
)

found_legacy=()
for f in "${LEGACY_FILES[@]}"; do
  if [ -f "$TARGET_DIR/$f" ]; then
    found_legacy+=("$f")
  fi
done

found_new=()
for f in "${LEGACY_FILES[@]}"; do
  if [ -f "$TARGET_DIR/${f}.new" ]; then
    found_new+=("${f}.new")
  fi
done

found_docs_ai=()
if [ -d "$TARGET_DIR/docs/ai" ]; then
  while IFS= read -r -d '' file; do
    rel="${file#$TARGET_DIR/}"
    found_docs_ai+=("$rel")
  done < <(find "$TARGET_DIR/docs/ai" -type f -print0 2>/dev/null)
fi

# ─── Build prompt ───────────────────────────────────────────────────────────

cat <<'PROMPT_START'
# Legacy AI State Migration

You are helping migrate legacy root-level AI-state files into the existing `docs/ai/` structure.

## STOP — Read this before doing anything

**The AI workflow template structure has already been installed.**
The `docs/ai/` directory and its template files exist. Your job is to migrate content
*into* those files — not to recreate, replace, or shorten them.

If any required `docs/ai/` file is missing, stop immediately and tell the user:
> "The docs/ai/ template structure is incomplete. Run `./scripts/install-ai-workflow.sh` first."

---

## Constraints — mandatory, no exceptions

1. Do NOT modify any production code.
2. Do NOT install dependencies.
3. Do NOT delete any files.
4. Do NOT archive or move any files.
5. Do NOT perform any git operations (no commits, no staging, no checkout).
6. Do NOT recreate, replace, or shorten any `docs/ai/` file that already exists.
7. Do NOT wholesale-replace target files — preserve every existing heading and section.
8. Merge strategy only: fill empty TODOs, fill existing sections, or append migrated content
   under a clearly marked subsection (e.g., `### Migrated from legacy TASKS.md`).
9. Mark unclear or ambiguous content as `TODO: unclear — needs human review`.
10. Leave all `.new` files and all legacy root files exactly where they are.
11. Git may not be available. Do not require or invoke git.
12. Before reporting `.new` file status, verify with: `find . -name "*.new" | sort`

---

## Allowed target files

Migration content may only be written into these files:

- `AGENTS.md`
- `CLAUDE.md`
- `docs/ai/PROJECT.md`
- `docs/ai/CURRENT.md`
- `docs/ai/TASKS.md`
- `docs/ai/DECISIONS.md`
- `docs/ai/HANDOFF.md`
- `docs/ai/RESEARCH.md` (only if it already exists)

---

## Forbidden files — never create or modify

Never create, modify, or write to any of the following, even if the legacy source mentions them:

- `docs/ai/CODE_REVIEW.md`
- `docs/ai/PROMPTS.md`
- `docs/ai/WORKFLOW.md`
- `docs/ai/LEGACY_MIGRATION.md`
- `CHANGELOG.md`
- `README.md`
- `scripts/*` (any file under scripts/)
- `*.py` files
- `requirements.txt`
- `launchagents/*`
- Any `*.new` file
- Any root-level legacy file (HANDOFF.md, TASKS.md, etc.)

---

## What to read first

Read all of the following files that exist in the project root and in `docs/ai/`:

### Root-level legacy files (may contain project-specific rules and state)
PROMPT_START

if [ ${#found_legacy[@]} -gt 0 ]; then
  for f in "${found_legacy[@]}"; do
    echo "- $f"
  done
else
  echo "- (none detected at prompt generation time — check manually)"
fi

cat <<'PROMPT_SECTION2'

### Candidate new template files (written by the installer; not yet merged)
PROMPT_SECTION2

if [ ${#found_new[@]} -gt 0 ]; then
  for f in "${found_new[@]}"; do
    echo "- $f"
  done
else
  echo "- (none detected at prompt generation time — check manually)"
fi

cat <<'PROMPT_SECTION3'

### Existing docs/ai/ files (installed by the template; may be empty stubs or partially filled)
PROMPT_SECTION3

if [ ${#found_docs_ai[@]} -gt 0 ]; then
  for f in "${found_docs_ai[@]}"; do
    echo "- $f"
  done
else
  echo "- (none detected — docs/ai/ may not exist yet)"
fi

cat <<'PROMPT_BODY'

---

## Migration mapping

Apply this mapping when migrating content. Only allowed target files are listed.
Content from forbidden-target legacy files (CODE_REVIEW.md, PROMPTS.md, WORKFLOW.md)
must be summarized into PROJECT.md or DECISIONS.md — do not create matching docs/ai/ files.

| Root file | Migrate to | Notes |
|---|---|---|
| `AGENTS.md` | `AGENTS.md` (keep in root) | Merge project-specific rules; use `AGENTS.md.new` as structure base if it exists |
| `CLAUDE.md` | `CLAUDE.md` (keep in root) | Merge project-specific Claude rules; use `CLAUDE.md.new` as structure base |
| `GEMINI.md` | `CLAUDE.md` or `AGENTS.md` notes | Extract any unique project-specific rules; Gemini-specific config is low priority |
| `PROJECT_STATE.md` | `docs/ai/PROJECT.md` + `docs/ai/CURRENT.md` | Persistent facts → PROJECT.md; live/active state → CURRENT.md |
| `PROJECT.md` | `docs/ai/PROJECT.md` | Merge into stub; prefer existing docs/ai content if richer |
| `CURRENT.md` | `docs/ai/CURRENT.md` | Merge working state; preserve existing docs/ai headings |
| `HANDOFF.md` | `docs/ai/HANDOFF.md` | Merge handoff content; preserve existing docs/ai headings |
| `TASKS.md` | `docs/ai/TASKS.md` | Merge task board; append under `### Migrated from legacy TASKS.md` if conflict |
| `DECISIONS.md` | `docs/ai/DECISIONS.md` | Merge ADRs; append under `### Migrated from legacy DECISIONS.md` if needed |
| `RESEARCH.md` | `docs/ai/RESEARCH.md` (if it exists) or summarize into `docs/ai/PROJECT.md` | Keep if valuable; summarize if large |
| `CODE_REVIEW.md` | _(forbidden target)_ — summarize key rules into `docs/ai/DECISIONS.md` | Do not create docs/ai/CODE_REVIEW.md |
| `PROMPTS.md` | _(forbidden target)_ — skip or note in report | Do not create docs/ai/PROMPTS.md |
| `WORKFLOW.md` | _(forbidden target)_ — summarize key workflow rules into `docs/ai/PROJECT.md` | Do not create docs/ai/WORKFLOW.md |

---

## How to handle `.new` files

A `.new` file (e.g., `AGENTS.md.new`) is the fresh template version written by the installer.
It was not installed directly because an older file already existed.

Rules:
- Treat the `.new` file as the **structural template** (preferred structure and sections).
- Treat the existing root file as the **source of project-specific content**.
- Merge: use `.new` structure + add project-specific content from the old file.
- If the old file and `.new` have conflicting generic content, prefer `.new`.
- If the old file has project-specific rules not in `.new`, preserve them in a clearly marked section.
- Do NOT delete or modify any `.new` file.

---

## How to handle docs/ai/ files

The `docs/ai/` files may be:
- Empty stubs (just installed, never filled in)
- Partially filled (some content from a previous session)

Rules:
- **Never wholesale-replace** a `docs/ai/` file. Preserve all existing headings and sections.
- If a `docs/ai/` file is an empty stub, migrate content from the corresponding root file.
- If a `docs/ai/` file already has content, merge carefully — do not overwrite real project state.
- Append migrated content under a clearly labeled subsection, e.g.:
  `### Migrated from legacy TASKS.md`
- If `docs/ai/RESEARCH.md` does not exist, do not create it — summarize into `docs/ai/PROJECT.md` instead.

---

## Step-by-step process

1. Check that all required `docs/ai/` files exist. If any are missing, stop and report.
2. Read every file listed above (legacy root files, `.new` files, docs/ai/ files).
3. For each file in the migration mapping table:
   a. Confirm the target is in the allowed list. Skip if forbidden.
   b. Check if the source (root file) exists and has project-specific content.
   c. Check if the target (docs/ai/ file) exists and has content.
   d. Check if a `.new` file exists for this path.
   e. Decide: merge into existing section, append under new subsection, or skip — explain why.
4. Perform the migration writes (allowed targets only).
5. Leave all legacy root files and `.new` files in place.
6. Run: `find . -name "*.new" | sort` — include the output in the report.
7. Produce the migration report (see format below).

---

## Migration report format

After completing migration, output a report in this exact format:

```
## Legacy AI State Migration Report

### Files migrated
| Source | Target | Action taken |
|---|---|---|
| (file) | (file) | created / merged / appended / skipped — reason |

### Forbidden files check
Confirm: none of the following were created or modified:
docs/ai/CODE_REVIEW.md, docs/ai/PROMPTS.md, docs/ai/WORKFLOW.md,
docs/ai/LEGACY_MIGRATION.md, CHANGELOG.md, README.md, scripts/*, *.py,
requirements.txt, launchagents/*, *.new files, root legacy files

### .new file status
Output of: find . -name "*.new" | sort
(all .new files must still be present and unmodified)

### Content migrated
For each migrated file: 2–3 bullet points on what was moved.

### Unclear content
List anything kept as TODO, with a brief explanation of why it was unclear.

### Files left in place
List all legacy root files and .new files that were not modified.

### Recommended next steps
1. Human review: which files should be verified before archiving legacy files
2. Archival candidates: which root files are safe to archive once verified
   Recommended archive path: _archive/legacy-ai-state/
3. Any remaining TODOs that require human input

### Warning
Do NOT delete or archive any root legacy file until a human has verified
that the migrated docs/ai/ version is complete and accurate.
At minimum, validate with one agent session that reads docs/ai/ and produces
a coherent project summary.
```

---

## Tool guidance

**Prefer Claude Code or Codex for a full legacy migration** — they provide the strongest
multi-file reasoning and will respect these constraints most reliably.

**Use Gemini only for small, phased tasks** such as:
- Analyzing a single legacy file and summarizing its content
- Reviewing the migration report after Claude Code or Codex has done the writes
- Consistency-checking docs/ai/ files post-migration

If Gemini is used for the full migration, review every write carefully before accepting.

---

Begin. Verify that all required docs/ai/ files exist first — stop and report if any are missing.
Then read all listed files, then produce the migration plan before making any changes.
PROMPT_BODY

#!/usr/bin/env bash
# ai-handoff-prompt.sh
# Outputs a handoff prompt to trigger end-of-session updates.
# Usage: ./scripts/ai-handoff-prompt.sh | pbcopy
# Then paste into the current agent session before closing.

set -euo pipefail

cat << 'PROMPT'
This session is ending. Before stopping, update the following three files.
The handoff must be complete enough that another agent can continue
without any chat history or additional context from you.

─────────────────────────────────────────────
UPDATE: docs/ai/CURRENT.md
─────────────────────────────────────────────
Fill in or update:
- Last updated: today's date and time
- Updated by: your agent name (Claude Code / Codex / Gemini)
- Current goal: what was being worked on
- Current branch: the active git branch
- Status:
  - Done: what was completed this session
  - In Progress: what is still in progress
  - Blocked: any blockers and what is needed to unblock
- Relevant files: list files central to the current work
- Current git state: branch and modified files
- Known problems: any bugs or errors discovered
- Assumptions: any assumptions made that need verification
- Next step: one specific, actionable next step

─────────────────────────────────────────────
UPDATE: docs/ai/TASKS.md
─────────────────────────────────────────────
- Move completed tasks to the Done section (mark as [x])
- Move newly discovered tasks to Next or Parking Lot
- Update Blocked with any new blockers
- Remove tasks from In Progress that are now done

─────────────────────────────────────────────
UPDATE: docs/ai/HANDOFF.md
─────────────────────────────────────────────
Fill in:
- Last updated: today's date and time
- Updated by: your agent name
- Handoff to: next intended agent or "unspecified"
- Short summary: 2–3 sentences on the current situation
- Last action: the very last thing done before this handoff
- Changed files: a table of all files modified/created/deleted this session
- Open items: what is incomplete or left for the next session
- Risks / Attention: what could break, what is fragile, what to watch out for
- Checks: what was verified (typecheck, tests, lint, manual test) and the results
- Next concrete action: one specific, actionable instruction for the next agent
- Ideal next prompt: a ready-to-copy prompt that the next agent can use immediately

After updating all three files, output a brief confirmation:
- List the files you updated
- State the next concrete action in one sentence
PROMPT

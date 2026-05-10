#!/usr/bin/env bash
# ai-start.sh
# Outputs a start prompt for a new AI agent session.
# Usage: ./scripts/ai-start.sh | pbcopy
# Then paste into Claude Code, Codex, or Gemini.

set -euo pipefail

cat << 'PROMPT'
Read the following files in order before doing anything else:

1. AGENTS.md
2. docs/ai/PROJECT.md
3. docs/ai/CURRENT.md
4. docs/ai/TASKS.md
5. docs/ai/DECISIONS.md
6. docs/ai/HANDOFF.md
7. docs/ai/CODE_REVIEW.md
8. docs/ai/WORKFLOW.md

After reading all files, summarize your understanding in up to 10 bullet points:

1. What this project is and its tech stack
2. What is the current active goal
3. Which branch we are on
4. What was last done (from HANDOFF.md)
5. What the immediate next task is
6. Which files are most relevant right now
7. Any blockers or risks noted
8. Any open items from the last session
9. Any decisions in DECISIONS.md that constrain the current work
10. Your recommended first action

Important:
- Do NOT make any file changes yet.
- Do NOT start implementation.
- Only read and summarize.
- If the AI state files contain contradictions, point them out before proceeding.
- If HANDOFF.md or CURRENT.md are empty or outdated, say so explicitly.
PROMPT

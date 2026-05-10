#!/usr/bin/env bash
# ai-review-prompt.sh
# Outputs a code review prompt for the current git diff.
# Usage: ./scripts/ai-review-prompt.sh | pbcopy
# Best used with Gemini to avoid burning Claude Code context.

set -euo pipefail

cat << 'PROMPT'
Read the following files before starting the review:

1. AGENTS.md
2. docs/ai/PROJECT.md
3. docs/ai/CODE_REVIEW.md
4. docs/ai/HANDOFF.md

Then review the current git diff. Use:
  git diff HEAD
  git diff --staged
  (or the specific files/PR described below)

Apply the full checklist from docs/ai/CODE_REVIEW.md. Check for:

- Correctness: edge cases, error handling, async issues, race conditions
- Type safety: TypeScript types, nullable handling, unintended `any`
- Architecture: adherence to PROJECT.md conventions, layer violations, DECISIONS.md
- Tests: missing test coverage, untested edge cases, deleted tests
- UI/UX: loading state, error state, mobile, keyboard navigation (if UI changed)
- Accessibility: labels, ARIA, focus management (if UI changed)
- Performance: N+1 queries, missing memoization, large unoptimized imports
- Security: input sanitization, auth checks, exposed secrets, SQL/XSS injection
- Maintainability: dead code, naming, style consistency
- Handoff consistency: does HANDOFF.md accurately reflect what was changed?

Output your review in this exact format:

## Code Review — [date]

**Reviewer:** [your agent name]
**Reviewed:** [files or diff description]

### 1. Critical Issues
[must be fixed before merge — or write "None."]

### 2. Non-blocking Suggestions
[advisory improvements — write "None." if none]

### 3. Missing Tests
[test cases that should exist — write "None." if none]

### 4. Risk Level
**Low** | **Medium** | **High**
Reason: [brief explanation]

### 5. Recommended Next Action
[one concrete sentence]

Rules for this review:
- Do NOT modify any file.
- Do NOT suggest rewrites unless they address a Critical issue.
- Do NOT block on style issues — note them as Non-blocking Suggestions only.
PROMPT

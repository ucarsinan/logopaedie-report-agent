#!/usr/bin/env bash
# ai-bootstrap-project.sh
# Outputs a prompt that instructs an agent to analyze the project
# and fill in the AI context files (PROJECT.md, CURRENT.md, TASKS.md, HANDOFF.md).
# Usage: ./scripts/ai-bootstrap-project.sh | pbcopy
# Recommended tool: Gemini (no implementation cost, good at analysis)

set -euo pipefail

cat << 'PROMPT'
Your task: analyze this project and fill in the AI context files.

─────────────────────────────────────────────
STEP 1 — Read these files to understand the project:
─────────────────────────────────────────────
- package.json (or requirements.txt / pyproject.toml / Cargo.toml — whatever exists)
- README.md (and any other markdown documentation in the root)
- Any config files: tsconfig.json, next.config.*, vite.config.*, .eslintrc*, prettier.config.*
- The top-level directory structure (list files and folders)
- Any existing test files (to understand test runner and patterns)
- Any existing CI/CD config (.github/workflows/, etc.)
- docs/ai/PROJECT.md (to see what is already filled in)

─────────────────────────────────────────────
STEP 2 — Update ONLY these four files:
─────────────────────────────────────────────

1. docs/ai/PROJECT.md
   Fill in every TODO section you can determine with confidence:
   - Project name, purpose, status
   - Tech stack table (language, runtime, framework, frontend, styling, backend, DB, auth, hosting)
   - Package manager and available commands (dev, build, test, typecheck, lint, format)
   - Repository structure (copy the key parts of the directory tree)
   - Coding conventions (if visible from config files or code patterns)
   - Known constraints and fragile areas (if visible from README or code)
   - Environment variables (list variable names from .env.example or README)

2. docs/ai/CURRENT.md
   Fill in:
   - Last updated: today's date
   - Updated by: your agent name
   - Current goal: "Initial AI workflow setup — PROJECT.md population"
   - Current branch: (check with git branch --show-current)
   - Status: Done = "AI workflow installed, PROJECT.md populated"; In Progress = ""; Blocked = ""
   - Next step: "Human: review docs/ai/PROJECT.md and fill in any remaining TODOs"

3. docs/ai/TASKS.md
   Add these tasks:
   - Done: "Install AI workflow infrastructure"
   - Next: "Human review of docs/ai/PROJECT.md — verify all TODOs are filled"
   - Next: "Run first real AI session with ai-start.sh"

4. docs/ai/HANDOFF.md
   Fill in:
   - Summary: "AI workflow installed and PROJECT.md bootstrapped from existing project files."
   - Last action: "Populated docs/ai/PROJECT.md based on project analysis"
   - Changed files: docs/ai/PROJECT.md, docs/ai/CURRENT.md, docs/ai/TASKS.md, docs/ai/HANDOFF.md
   - Open items: remaining TODOs in PROJECT.md that need human input
   - Risks: none at this stage
   - Next concrete action: "Human: review docs/ai/PROJECT.md and fill in remaining TODOs. Then run: ./scripts/ai-start.sh | pbcopy"

─────────────────────────────────────────────
RULES:
─────────────────────────────────────────────
- Do NOT modify any production code, tests, config files, or dependencies.
- Do NOT install anything.
- Do NOT run any commands that affect external services.
- If you are uncertain about a value, write "TODO: [what needs to be confirmed]" instead of guessing.
- If a value is genuinely unclear from the project files, write "Unclear — needs human input."
- Never invent API endpoints, database schemas, or deployment URLs.
- Stick to what is visible in the project files.

After updating all four files, output a brief summary:
- What was filled in
- What TODOs remain for the human
- What the recommended next step is
PROMPT

#!/usr/bin/env bash
# ai-status.sh
# Prints a compact status summary: git state + AI context files.
# Usage: ./scripts/ai-status.sh

set -uo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RESET='\033[0m'

section() { echo -e "\n${BLUE}━━━ $* ━━━${RESET}"; }
label()   { echo -e "${GREEN}$*${RESET}"; }
missing() { echo -e "${YELLOW}[not found]${RESET}"; }

print_file() {
  local path="$1"
  local title="$2"
  section "$title"
  if [ -f "$path" ]; then
    cat "$path"
  else
    missing
    echo "Expected: $path"
  fi
}

section "Git Status"
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  label "Branch:"
  git branch --show-current 2>/dev/null || echo "unknown"
  echo ""
  label "Status:"
  git status --short 2>/dev/null || echo "(no git status)"
  echo ""
  label "Last 5 commits:"
  git log --oneline -5 2>/dev/null || echo "(no commits)"
else
  missing
  echo "Not in a git repository or git not available."
fi

print_file "docs/ai/CURRENT.md" "CURRENT.md"
print_file "docs/ai/HANDOFF.md" "HANDOFF.md"
print_file "docs/ai/TASKS.md"   "TASKS.md"

echo ""
echo -e "${BLUE}━━━ End of Status ━━━${RESET}"
echo ""

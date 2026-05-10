# PROMPTS.md — Reusable Agent Prompts

> Copy-paste ready prompts for common AI workflow operations.
> Adapt the TODO sections to your current situation before using.

---

## 1. Start Prompt — New Agent Session

Use this at the beginning of any agent session.

```text
Read the following files in order before doing anything else:
- AGENTS.md
- docs/ai/PROJECT.md
- docs/ai/CURRENT.md
- docs/ai/TASKS.md
- docs/ai/DECISIONS.md
- docs/ai/HANDOFF.md
- docs/ai/CODE_REVIEW.md
- docs/ai/WORKFLOW.md

After reading, summarize your understanding in up to 10 bullet points:
1. What this project is and its tech stack
2. What is the current active goal
3. What branch we are on
4. What was last done (from HANDOFF.md)
5. What the next task is
6. Which files are most relevant right now
7. Any blockers or risks noted
8. Any open items from the last session
9. Any decisions that constrain the current work
10. Your recommended first action

Do NOT make any file changes yet. Only summarize.
```

---

## 2. Handoff Prompt — End of Session

Use this when finishing a session to ensure a clean handoff.

```text
This session is ending. Before stopping, update the following files:

1. docs/ai/CURRENT.md
   - Last updated: [today's date and time]
   - Updated by: [your agent name]
   - Current goal: [what we were working on]
   - Status: what is done, in progress, and blocked
   - Relevant files: list the files that matter right now
   - Current git state: branch and modified files
   - Known problems: any bugs or errors discovered
   - Next step: one concrete next action

2. docs/ai/TASKS.md
   - Move completed tasks to Done
   - Move newly discovered tasks to Next or Parking Lot
   - Update Blocked with any new blockers

3. docs/ai/HANDOFF.md
   - Short summary: 2-3 sentences on the current situation
   - Last action: what was the very last thing done
   - Changed files: table of all files modified this session
   - Open items: what is incomplete
   - Risks: what could break or needs attention
   - Checks: what was verified (typecheck, tests, lint, manual test)
   - Next concrete action: one specific instruction for the next agent
   - Ideal next prompt: a ready-to-copy prompt for the next agent

The handoff must be complete enough that another agent can continue
without any chat history or additional context from you.
```

---

## 3. Codex Takeover Prompt — After Hitting a Limit

Use this when starting a fresh Codex session after a context or rate limit.

```text
I am starting a fresh Codex session. The previous session hit its context limit.

Read these files to understand the current situation:
- docs/ai/HANDOFF.md  ← start here
- docs/ai/CURRENT.md
- docs/ai/TASKS.md
- docs/ai/PROJECT.md
- AGENTS.md (your canonical instruction file — there is no CODEX.md)

Then run: git diff HEAD
Inspect any uncommitted changes left by the previous agent before proceeding.

Follow the "Next Concrete Action" and "Ideal Next Prompt" in HANDOFF.md.
Do not ask me to re-explain context — everything is in those files.
After completing the task, update CURRENT.md, TASKS.md, and HANDOFF.md.
```

---

## 3a. Claude Code Takeover Prompt — After Hitting a Limit

Use this when starting a fresh Claude Code session after a context or rate limit.

```text
I am starting a fresh Claude Code session. The previous session hit its context limit.

Read these files to understand the current situation:
- docs/ai/HANDOFF.md  ← start here
- docs/ai/CURRENT.md
- docs/ai/TASKS.md
- docs/ai/PROJECT.md
- AGENTS.md

Then run: git diff HEAD
Inspect any uncommitted changes left by the previous agent before proceeding.

Follow the "Next Concrete Action" and "Ideal Next Prompt" in HANDOFF.md.
Do not ask me to re-explain context — everything is in those files.
After completing the task, update CURRENT.md, TASKS.md, and HANDOFF.md.
```

---

## 4. Gemini Review Prompt

Use this to trigger a code review via Gemini.

```text
Read the following files:
- AGENTS.md
- docs/ai/PROJECT.md
- docs/ai/CODE_REVIEW.md
- docs/ai/HANDOFF.md

Then review the current git diff (`git diff HEAD` or the staged changes).

Apply the full checklist from CODE_REVIEW.md.

Output your review in the format defined in CODE_REVIEW.md:
1. Critical Issues
2. Non-blocking Suggestions
3. Missing Tests
4. Risk Level (low / medium / high) with reason
5. Recommended Next Action

Do NOT make any file changes. Output only the review.
```

---

## 5. Gemini Planning Prompt

Use this to get a structured implementation plan from Gemini before starting work.

```text
Read the following files:
- docs/ai/PROJECT.md
- docs/ai/CURRENT.md
- docs/ai/TASKS.md
- docs/ai/DECISIONS.md

The current goal is: [TODO: describe the goal in one sentence]

Produce an implementation plan:
1. Restate the goal and success criteria
2. Break the goal into concrete subtasks (max 7)
3. For each subtask: which files need to change and why
4. Identify risks, edge cases, and potential breaking changes
5. Identify what can be deferred to a later session
6. Suggest which tasks are suitable for Gemini vs. Claude Code / Codex
7. Estimate risk level: low / medium / high

Do NOT write any code. Output only the plan.
After producing the plan, update docs/ai/TASKS.md with the subtasks.
```

---

## 6. Gemini Test Prompt

Use this to have Gemini write or expand tests.

```text
Read the following files:
- docs/ai/PROJECT.md
- docs/ai/CURRENT.md

The file(s) to test: [TODO: list file paths]
The test runner and conventions are described in PROJECT.md.

Write tests for:
- Happy path
- Common edge cases
- Error / failure cases

Follow the project's existing test patterns exactly.
Do NOT modify production code.
After writing tests, run them if possible and report results.
Then update docs/ai/TASKS.md and docs/ai/HANDOFF.md.
```

---

## 7. Documentation Prompt

Use this to update documentation after an implementation session.

```text
Read:
- docs/ai/PROJECT.md
- docs/ai/CURRENT.md
- docs/ai/HANDOFF.md

Then update documentation as follows:
1. Update README.md if the setup, usage, or API changed
2. Update any relevant inline comments if functions changed
3. Update docs/ai/PROJECT.md if the tech stack or conventions changed
4. Do NOT document internal implementation details — only what users or future developers need

Do NOT modify production code or tests.
After updating, write a brief summary of what was changed and why.
```

---

## 8. Handoff Consistency Check Prompt

Use this (ideally with Gemini) to verify the AI state files are internally consistent.

```text
Read all of these files:
- docs/ai/CURRENT.md
- docs/ai/TASKS.md
- docs/ai/HANDOFF.md
- docs/ai/PROJECT.md

Check for inconsistencies:
- Does CURRENT.md match HANDOFF.md on the current goal and last action?
- Are the tasks in TASKS.md consistent with what CURRENT.md says is done/in progress?
- Are the changed files in HANDOFF.md plausible given the current goal?
- Are there open items in HANDOFF.md that are not reflected in TASKS.md?
- Is the next step in CURRENT.md specific and actionable?

Report any inconsistencies you find.
If any file needs updating, list exactly what should change.
Do NOT make changes — only report.
```

---

## 9. Codex Implementation Prompt

Use this to start a focused Codex implementation task.

```text
Read AGENTS.md first — it is your canonical instruction file for this project.
There is no CODEX.md; AGENTS.md contains all project rules.

Then read:
- docs/ai/PROJECT.md
- docs/ai/CURRENT.md
- docs/ai/HANDOFF.md

Your task: [TODO: describe the specific task in one sentence]
Files to change: [TODO: list expected files]
Definition of done: [TODO: what does success look like?]
Constraints: [TODO: any specific rules, e.g., "do not change public API"]

Before writing any code:
1. Restate your understanding of the task
2. List the files you plan to touch
3. Identify any risks

Then implement. After implementation:
- Run available checks (typecheck, tests, lint) and report results
- Update docs/ai/CURRENT.md, docs/ai/TASKS.md, docs/ai/HANDOFF.md
```

---

## 9a. Codex Review Prompt

Use this when asking Codex to review code without making changes.

```text
Read:
- AGENTS.md
- docs/ai/PROJECT.md
- docs/ai/CODE_REVIEW.md

Enter review-only mode. Do NOT modify any files.

Review: [TODO: describe what to review — a file path, a diff, a PR]

Apply the full checklist from CODE_REVIEW.md.
Output your review in the format from CODE_REVIEW.md:
1. Critical Issues
2. Non-blocking Suggestions
3. Missing Tests
4. Risk Level (low / medium / high) with reason
5. Recommended Next Action

Do NOT write any code. Do NOT suggest rewrites unless they address a Critical issue.
```

---

## 9b. Claude Code Implementation Prompt

Use this to start a focused Claude Code implementation task.

```text
Read:
- AGENTS.md
- docs/ai/PROJECT.md
- docs/ai/CURRENT.md
- docs/ai/HANDOFF.md

Your task: [TODO: describe the specific task in one sentence]
Files to change: [TODO: list expected files]
Definition of done: [TODO: what does success look like?]
Constraints: [TODO: any specific rules, e.g., "do not change public API"]

Before writing any code:
1. Restate your understanding of the task
2. List the files you plan to touch
3. Identify any risks

Then implement. After implementation:
- Run available checks (typecheck, tests, lint)
- Update docs/ai/CURRENT.md, docs/ai/TASKS.md, docs/ai/HANDOFF.md
```

---

## 10. Legacy AI State Migration Prompt

Use this when an existing project already has root-level AI-state files and you need to migrate them into `docs/ai/`.

**Preferred tools:** Claude Code or Codex (strongest multi-file reasoning, most reliable constraint adherence).
**Gemini:** use only for small phased tasks — analysis of a single file, post-migration review, or consistency checks. Do not use Gemini for a full migration run.

**Prerequisite:** The `docs/ai/` template structure must already be installed. If any of the following are missing, run `./scripts/install-ai-workflow.sh` first before using this prompt:
- `docs/ai/PROJECT.md`, `docs/ai/CURRENT.md`, `docs/ai/TASKS.md`, `docs/ai/DECISIONS.md`, `docs/ai/HANDOFF.md`

This prompt is also available as a script that auto-detects which files exist (and verifies the prerequisite):

```bash
./scripts/ai-migrate-legacy-prompt.sh | pbcopy
# Paste into Claude Code or Codex (preferred) — or Gemini for small analysis tasks only
```

If you prefer to use the prompt directly, paste the following (adjust the file list to match what actually exists in your project root):

```text
# Legacy AI State Migration

You are helping migrate legacy root-level AI-state files into the existing docs/ai/ structure.

## STOP — Read this before doing anything

The AI workflow template structure has already been installed.
The docs/ai/ directory and its template files exist. Your job is to migrate content
*into* those files — not to recreate, replace, or shorten them.

If any required docs/ai/ file is missing, stop immediately and tell the user:
"The docs/ai/ template structure is incomplete. Run ./scripts/install-ai-workflow.sh first."

## Constraints — mandatory, no exceptions

1. Do NOT modify any production code.
2. Do NOT install dependencies.
3. Do NOT delete any files.
4. Do NOT archive or move any files.
5. Do NOT perform any git operations.
6. Do NOT recreate, replace, or shorten any docs/ai/ file that already exists.
7. Do NOT wholesale-replace target files — preserve every existing heading and section.
8. Merge strategy only: fill empty TODOs, fill existing sections, or append migrated
   content under a clearly marked subsection (e.g., ### Migrated from legacy TASKS.md).
9. Mark unclear content as: TODO: unclear — needs human review
10. Leave all .new files and all legacy root files exactly where they are.
11. Git may not be available. Do not require or invoke git.
12. Before reporting .new file status, verify with: find . -name "*.new" | sort

## Allowed target files

Migration content may only be written into:
- AGENTS.md
- CLAUDE.md
- docs/ai/PROJECT.md
- docs/ai/CURRENT.md
- docs/ai/TASKS.md
- docs/ai/DECISIONS.md
- docs/ai/HANDOFF.md
- docs/ai/RESEARCH.md (only if it already exists)

## Forbidden files — never create or modify

- docs/ai/CODE_REVIEW.md
- docs/ai/PROMPTS.md
- docs/ai/WORKFLOW.md
- docs/ai/LEGACY_MIGRATION.md
- CHANGELOG.md
- README.md
- scripts/* (any file under scripts/)
- *.py files
- requirements.txt
- launchagents/*
- Any *.new file
- Any root-level legacy file

## Read first

Read all of the following files that exist:
- Root: AGENTS.md, CLAUDE.md, GEMINI.md, HANDOFF.md, TASKS.md, DECISIONS.md,
        PROJECT_STATE.md, PROJECT.md, CURRENT.md, RESEARCH.md,
        CODE_REVIEW.md, PROMPTS.md, WORKFLOW.md
- Candidate templates: AGENTS.md.new, CLAUDE.md.new, GEMINI.md.new (if present)
- Existing docs/ai/ files: PROJECT.md, CURRENT.md, TASKS.md,
                            DECISIONS.md, HANDOFF.md (and RESEARCH.md if present)

## Migration mapping (allowed targets only)

- AGENTS.md.new → base for AGENTS.md; add project-specific rules from old AGENTS.md
- CLAUDE.md.new → base for CLAUDE.md; add project-specific rules from old CLAUDE.md
- Root PROJECT_STATE.md → docs/ai/PROJECT.md + docs/ai/CURRENT.md
- Root TASKS.md → docs/ai/TASKS.md (merge; append under subsection if conflict)
- Root DECISIONS.md → docs/ai/DECISIONS.md (merge; append under subsection if conflict)
- Root HANDOFF.md → docs/ai/HANDOFF.md (merge; preserve existing headings)
- Root RESEARCH.md → docs/ai/RESEARCH.md if it exists, else summarize into docs/ai/PROJECT.md
- Root CODE_REVIEW.md → summarize key rules into docs/ai/DECISIONS.md (do NOT create docs/ai/CODE_REVIEW.md)
- Root PROMPTS.md → skip or note in report (do NOT create docs/ai/PROMPTS.md)
- Root WORKFLOW.md → summarize key workflow rules into docs/ai/PROJECT.md (do NOT create docs/ai/WORKFLOW.md)

## After migration, produce a report

1. Files migrated (source → target, action taken)
2. Forbidden files check: confirm none were created or modified
3. .new file status: output of `find . -name "*.new" | sort`
4. Content migrated (2-3 bullets per file)
5. Unclear content (kept as TODO, with reason)
6. Files left in place (all legacy + .new files)
7. Recommended next steps and archival candidates
   (Recommended archive path: _archive/legacy-ai-state/)

Warning: Do NOT suggest deleting any legacy file. Human review is required first.
```

---

## 11. Review-Only Prompt

Use this when you want a review without any code changes.

```text
Read:
- AGENTS.md
- docs/ai/PROJECT.md
- docs/ai/CODE_REVIEW.md

Review the following: [TODO: describe what to review — a file, a diff, a PR]

Apply the CODE_REVIEW.md checklist.
Output your review in the format from CODE_REVIEW.md.

Do NOT make any changes to any file.
Do NOT suggest rewrites unless they address a Critical issue.
```

---

## 12. Gemini Delegation Prompt — After Codex or Claude Work

Use this to hand off to Gemini after a Codex or Claude Code implementation session.

```text
Read:
- AGENTS.md
- docs/ai/PROJECT.md
- docs/ai/HANDOFF.md
- docs/ai/CODE_REVIEW.md

A Codex / Claude Code session just finished implementing: [TODO: describe what was done]

Your role: [TODO: choose one or more]
  - Review the implementation against CODE_REVIEW.md
  - Write or expand tests for the changed files
  - Update documentation (README, inline comments, PROJECT.md if needed)
  - Verify CURRENT.md, TASKS.md, HANDOFF.md are consistent
  - Perform a risk analysis on the changes

The relevant diff: run `git diff HEAD` or `git diff [base-branch]` to see changes.

Do NOT rewrite production code unless you find a Critical issue.
After completing your task, update docs/ai/TASKS.md and docs/ai/HANDOFF.md.
```

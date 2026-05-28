# HANDOFF.md — Agent-to-Agent Handoff

> **This file enables any agent to continue work without chat history.**
> It must be updated at the end of every meaningful AI session.
> The rule: if the next agent cannot understand the situation from this file alone, the handoff is incomplete.

---

## Last Updated

- **Date:** 2026-05-28
- **Updated by:** Claude Code
- **Handoff to:** unspecified — owner is currently driving work themselves on the anamnesis area

---

## Short Summary

`main` is at `5bad1a7` on the remote; two local commits stacked on top:
`ded7c1a` (demo-mode persistence fix in module router) and `4d1f0f6`
(CI bump — JS actions to v6, Node-24-native, drop opt-in env flag). Both
items are now off the `TASKS.md` "Next" column. The 2026-05-26 audit
backlog is still down to **M-6** (anamnesis completion logic), blocked
on owner-driven WIP in the anamnesis engine / phonological analyzer
area (do not touch).

---

Bumped the three JS-based actions in `.github/workflows/ci.yml` to v6
(`actions/checkout@v4→v6`, `actions/setup-node@v4→v6`,
`actions/setup-python@v5→v6`) and removed the
`FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` env flag + its comment block.
YAML validated locally. Two parallel agents (repo audit + v5→v6
changelog review) confirmed (a) no other stale action pins or Node-20
references in the repo, and (b) no breaking changes between v4/v5 and v6
affect our specific usage (parameterless checkout; explicit `cache:` +
`cache-dependency-path:` on setup-node and setup-python). Real CI
verification pending push.

Prior step in the same session: `ded7c1a` swapped the inline
`searchParams.get("demo") === "true"` check in
`frontend/src/app/module/[slug]/page.tsx` for the shared `useDemoMode()`
hook (URL **or** persisted localStorage). `tsc --noEmit` clean,
`vitest run` 146/146 green.

---

## Today's PRs (chronological)

| PR | Subject | Result |
| --- | --- | --- |
| [#3](https://github.com/ucarsinan/logopaedie-report-agent/pull/3) | Security & quality audit fixes (C-1/C-2, H-1..H-4, M-1/2/3/5, L-2/3/4) | merged 2026-05-27 (`b33cf7e`) |
| [#4](https://github.com/ucarsinan/logopaedie-report-agent/pull/4) | `fix(ci): drop NEXT_PUBLIC_API_URL override in E2E job` | merged 2026-05-27 (`5a00a3e`) — full E2E suite green |
| [#5](https://github.com/ucarsinan/logopaedie-report-agent/pull/5) | `docs: sync CLAUDE.md and docs/ai/PROJECT.md with current architecture (M-4)` | merged 2026-05-28 (`e8fe12b`) |
| [#6](https://github.com/ucarsinan/logopaedie-report-agent/pull/6) | `chore(ci): opt JS actions into Node.js 24 ahead of 2026-06-02 cutover` | merged 2026-05-28 (`9119077`) — all 7 jobs green on Node 24 |

---

## Changed Files (this session, beyond the per-PR diffs)

| File | Change | Notes |
| --- | --- | --- |
| `.github/workflows/ci.yml` | modified | PR #4 (env removal) + PR #6 (Node 24 opt-in) |
| `CLAUDE.md` | modified | PR #5 — synced with auth/patients/admin/BFF reality |
| `docs/ai/PROJECT.md` | modified | PR #5 — same sync |
| `docs/ai/CURRENT.md` | modified | this state-file sync |
| `docs/ai/TASKS.md` | modified | this state-file sync |
| `docs/ai/HANDOFF.md` | modified | this file |
| `frontend/src/app/module/[slug]/page.tsx` | modified → committed (`ded7c1a`) | demo-mode persistence fix — swap URL-only check for `useDemoMode()` hook |
| `.github/workflows/ci.yml` | modified → committed (`4d1f0f6`) | v6 action bump + drop `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` env flag |

Plus three local branches deleted (`claude-security-fixes`,
`feat/anamnese-slot-flow`, `security-audit-followup`) and the obsolete
`project_security_quarantine_branch.md` memory entry removed.

---

## Open Items

- [ ] **M-6** — anamnesis completion logic, blocked on owner WIP.
- [ ] Optional follow-up: align `frontend/package.json` `@types/node` from
      `^20` to `^22` (matches CI runtime; devDep only, not blocking).
- [ ] Pre-existing Vercel preview deploy failure — not a CI job, separate
      deployment-config issue. Out of scope unless explicitly requested.

---

## Risks / Attention

- **Owner WIP** in `backend/services/anamnesis_engine.py`,
  `backend/services/phonological_analyzer.py`,
  `backend/tests/test_phonological_analyzer.py` — do **not** stage, commit,
  or modify these. They were untouched by every agent commit today and
  must remain so.
- **NEXT_PUBLIC_API_URL trap**: don't reintroduce an absolute host value in
  the frontend-e2e CI job — see the comment block in `.github/workflows/ci.yml`.
  It is baked into the production bundle at `npm run build` and breaks the
  `**/backend-api/**` Playwright mocks (root cause of the recent E2E
  failures fixed by PR #4).
- **Node.js 20 → 24 forced cutover on 2026-06-02.** Currently mitigated by
  the workflow-level env flag from PR #6. Bumping to Node-24-native action
  versions before then makes the flag obsolete.
- Vercel `experimentalServices` is beta and may change without notice.

---

## Checks

| Check | Status | Notes |
| --- | --- | --- |
| `python -m pytest` (backend) | passed in PR #6 CI (1m9s) | ~270 functions across ~60 files |
| `npx playwright test` (E2E) | passed in PR #6 CI (1m15s) | 32 cases / 11 specs, chromium-only |
| `npm test` (frontend unit) | passed in PR #6 CI (1m8s) | |
| `npm run build` | passed | with `/backend-api` default, **not** absolute host |
| `ruff check`, `mypy`, `eslint`, `tsc` | passed in PR #6 CI | |
| Vercel deploy | **fails** (pre-existing) | separate from CI; ignore for green-up |

---

## Next Concrete Action

Push the two local commits (`ded7c1a` + `4d1f0f6`) to `origin/main`
(`git push`). After that, wait for the owner's anamnesis WIP to settle
or pick the next agent-safe item from `TASKS.md` "Next" column (UI
loading skeletons, PDF export quality, or backend test coverage for
therapy-plan / SOAP / compare — none touch the anamnesis files).

---

## Ideal Next Prompt

```text
Read docs/ai/HANDOFF.md, docs/ai/CURRENT.md, and docs/ai/PROJECT.md first.

Current situation: main is at 5bad1a7, fully in sync with origin/main,
working tree clean. The 2026-05-26 audit backlog is down to M-6
(anamnesis completion logic). M-6 is blocked on owner WIP in
backend/services/anamnesis_engine.py + phonological_analyzer.py — do NOT
touch those files until I tell you the WIP is settled.

Your task: <one of>
  (a) wait for me to hand off M-6 and confirm WIP is clear;
  (b) pick the next agent-safe item from docs/ai/TASKS.md "Next" column
      (UI skeletons, PDF quality, or backend test coverage — none touch
      the anamnesis files);
  (c) <my custom direction>.

After completing the task, update docs/ai/CURRENT.md, docs/ai/TASKS.md, and
docs/ai/HANDOFF.md before stopping.
```

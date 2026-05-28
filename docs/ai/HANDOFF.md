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

`main` is at `a3ba15a` on the remote; three local commits stacked on
top, all from the demo-mode follow-up work surfaced by the parallel
code-review + repo-scan agents that ran after `ded7c1a`:

- `129333c` — `refactor(frontend): centralize demo_mode access in useDemoMode`
- `cbf4d72` — `fix(frontend): reset dismissed picker state on module slug change`
- `11540d1` — `refactor(frontend): extract useOnboarding hook from module layout`

The 2026-05-26 audit backlog is still down to **M-6** (anamnesis
completion logic), blocked on owner-driven WIP in the anamnesis engine /
phonological analyzer area (do not touch).

---

## Last Action

Three follow-ups, in order:

1. **Centralized `"demo_mode"` access.** Added `getDemoMode()` (one-shot
   snapshot, robust `URLSearchParams` parse — no more
   `window.location.search.includes("demo=true")` matching `?xdemo=true`)
   and `setDemoMode(value)` (writes + dispatches a same-tab
   `demo-mode-changed` event so `useSyncExternalStore` consumers like
   `DemoBanner` re-render). Migrated four call sites:
   `features/report/ReportModule.tsx` (init read + `onDemo` setter),
   `features/auth/components/LoginForm.tsx`, and
   `features/auth/hooks/useRegister.ts`. +7 vitest cases on the hook.
2. **Reset `dismissed` on slug change.** `ModuleContent` in
   `app/module/[slug]/page.tsx` now calls
   `useEffect(() => setDismissed(false), [slug])`. Latent issue exposed
   by `ded7c1a` because the localStorage-backed `isDemo` no longer
   re-evaluates on URL change.
3. **Extracted `useOnboarding` hook.** Same shape as `useDemoMode`:
   `useSyncExternalStore`-backed reactive hook + `markOnboardingDone()`
   / `resetOnboarding()` helpers + same-tab `onboarding-changed` event.
   `module/layout.tsx` dropped the `setTimeout(0)` workaround.
   +5 vitest cases.

`tsc --noEmit` clean across all three. Full vitest suite has 1
unrelated failure in
`features/report/__tests__/ReportModule.test.tsx > recovers from a
stale-session 404 ...` — that test is owner WIP (depends on an unmerged
`ApiError` extraction in `frontend/src/lib/api.ts`) and is left in the
working tree for the owner to commit.

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
| `frontend/src/app/module/[slug]/page.tsx` | modified → committed (`ded7c1a`, then `cbf4d72`) | demo-mode persistence fix; dismissed reset on slug change |
| `.github/workflows/ci.yml` | modified → committed (`4d1f0f6`) | v6 action bump + drop `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` env flag |
| `frontend/src/hooks/useDemoMode.ts` | modified → committed (`129333c`) | added `getDemoMode` + `setDemoMode` exports, same-tab event dispatch |
| `frontend/src/hooks/__tests__/useDemoMode.test.ts` | modified → committed (`129333c`) | +7 cases (11 → 18) |
| `frontend/src/features/report/ReportModule.tsx` | modified → committed (`129333c`) | init read via `getDemoMode`, `onDemo` via `setDemoMode` |
| `frontend/src/features/auth/components/LoginForm.tsx` | modified → committed (`129333c`) | clear via `setDemoMode(false)` |
| `frontend/src/features/auth/hooks/useRegister.ts` | modified → committed (`129333c`) | clear via `setDemoMode(false)` |
| `frontend/src/hooks/useOnboarding.ts` | added → committed (`11540d1`) | new hook + `markOnboardingDone` + `resetOnboarding` |
| `frontend/src/hooks/__tests__/useOnboarding.test.ts` | added → committed (`11540d1`) | 5 cases |
| `frontend/src/app/module/layout.tsx` | modified → committed (`11540d1`) | use the hook + helper instead of direct `localStorage` calls |
| `frontend/src/lib/api.ts` | modified (uncommitted) | **owner WIP** — `ApiError` class extraction |
| `frontend/src/features/report/__tests__/ReportModule.test.tsx` | modified (uncommitted) | **owner WIP** — stale-session 404 recovery test depending on `ApiError` |

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
- **Additional uncommitted owner WIP** in `frontend/src/lib/api.ts`
  (adds an `ApiError` class) and
  `frontend/src/features/report/__tests__/ReportModule.test.tsx`
  (adds a stale-session 404 recovery test that depends on `ApiError`).
  Surfaced mid-session; `129333c` was isolated so it does not bundle
  this WIP. One vitest case currently fails because the matching
  production-code change in `ReportModule.tsx` was not in the working
  tree at commit time — owner is the one to land the full extraction.
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

Push the three local commits (`129333c` + `cbf4d72` + `11540d1`) to
`origin/main` (`git push`). Decide separately how to land the
uncommitted `ApiError`-extraction WIP in `frontend/src/lib/api.ts` +
`features/report/__tests__/ReportModule.test.tsx` — the failing
stale-session 404 test will turn green once the matching production-code
change is reintroduced into `ReportModule.tsx`. After that, wait for
the owner's anamnesis WIP to settle or pick the next agent-safe item
from `TASKS.md` "Next" column (UI loading skeletons, PDF export quality,
or backend test coverage for therapy-plan / SOAP / compare — none touch
the anamnesis files).

---

## Ideal Next Prompt

```text
Read docs/ai/HANDOFF.md, docs/ai/CURRENT.md, and docs/ai/PROJECT.md first.

Current situation: main is 3 commits ahead of origin/main (a3ba15a) —
129333c, cbf4d72, 11540d1 — all frontend follow-ups to the demo-mode
persistence fix. The 2026-05-26 audit backlog is down to M-6
(anamnesis completion logic). M-6 is blocked on owner WIP in
backend/services/anamnesis_engine.py + phonological_analyzer.py — do NOT
touch those files until I tell you the WIP is settled. Also leave the
uncommitted `ApiError` extraction in `frontend/src/lib/api.ts` +
`features/report/__tests__/ReportModule.test.tsx` alone until handed
over.

Your task: <one of>
  (a) wait for me to hand off M-6 and confirm WIP is clear;
  (b) pick the next agent-safe item from docs/ai/TASKS.md "Next" column
      (UI skeletons, PDF quality, or backend test coverage — none touch
      the anamnesis files);
  (c) <my custom direction>.

After completing the task, update docs/ai/CURRENT.md, docs/ai/TASKS.md, and
docs/ai/HANDOFF.md before stopping.
```

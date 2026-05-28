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

`main` is at `a3ba15a` on the remote; five local commits stacked on top,
the three earlier demo-mode follow-ups plus two new ones from this
session:

- `129333c` — `refactor(frontend): centralize demo_mode access in useDemoMode`
- `cbf4d72` — `fix(frontend): reset dismissed picker state on module slug change`
- `11540d1` — `refactor(frontend): extract useOnboarding hook from module layout`
- `fc2cab1` — `fix(frontend): derive onboarding overlay visibility instead of setState-in-effect`
- `339b7a4` — `feat(frontend): handle stale-session 404 via SessionProvider helper`

Working tree has four further uncommitted follow-ups to `339b7a4` (wire
`ReportModule.generateReport` into the helper, polish SOAP coverage,
refine `stale-session.ts`).

The 2026-05-26 audit backlog is still down to **M-6** (anamnesis
completion logic), blocked on owner-driven WIP in the anamnesis engine /
phonological analyzer area (do not touch).

---

## Last Action

Live `POST /backend-api/sessions/37b2eeabab65/generate` returned 404 in
the dev UI. Direct backend probe confirmed the body
`{"detail":"Session nicht gefunden oder abgelaufen."}` — the BFF proxy
was fine, the Redis-backed session simply did not exist (TTL or restart).
We hardened the UX so the next stale-session 404 recovers cleanly
instead of dumping the raw backend message:

1. **`ApiError` in `@/lib/api`.** `fetchApi` now throws an `ApiError`
   carrying the HTTP `status` instead of a plain `Error`. Backwards
   compatible — `ApiError extends Error`, so existing `err.message`
   handlers keep working.
2. **`@/lib/stale-session` util.** New module exposes
   `SESSION_STORAGE_KEY`, `STALE_SESSION_TOAST`, `isStaleSessionError`
   (duck-typed on numeric `status === 404` so HMR / loading order can't
   break detection), and `clearStoredSession` (removes the persisted id
   and fires the existing `__reportModuleReset` window bridge).
3. **`SessionProvider.handleStaleSession`.** New callback exposed on
   `useSession()` context: `clearStoredSession` + `setSessionId(null)` +
   `setMessages([])` + toast. `handleSoftReset` routes 404 from
   `api.sessions.newConversation` through it.
4. **Call-sites updated.** `ChatView` (anamnesis send loop) and
   `TherapyPlanModule` (both `chat` and `therapyPlan` catches) branch
   on `isStaleSessionError` before the generic error path. New
   regression test in `ReportModule.test.tsx` (mocks
   `api.sessions.generate` rejecting with `ApiError(404)` and asserts
   the recovery shape).

`tsc --noEmit` clean, full vitest suite **159 passed / 0 failed across
42 test files**. Lint clean on touched files (a single pre-existing
`react-hooks/set-state-in-effect` warning in
`app/module/[slug]/page.tsx` is not from this work).

Working tree carries four uncommitted follow-ups (matching the items in
`CURRENT.md`'s "Current Git State"): wire
`ReportModule.generateReport` into the helper (using the same
duck-typed `isStaleSessionError` / `STALE_SESSION_TOAST` from
`@/lib/stale-session`), plus SOAP coverage and a `stale-session.ts`
refinement.

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
| `frontend/src/lib/api.ts` | modified → committed (`339b7a4`) | `ApiError` class carrying `status` |
| `frontend/src/lib/stale-session.ts` | added → committed (`339b7a4`), further refined (uncommitted) | helper module: `isStaleSessionError`, `clearStoredSession`, constants |
| `frontend/src/providers/SessionProvider.tsx` | modified → committed (`339b7a4`) | `handleStaleSession` callback on context |
| `frontend/src/features/report/components/ChatView.tsx` | modified → committed (`339b7a4`) | `sendMessage` catch routes 404 through helper |
| `frontend/src/features/therapy-plan/TherapyPlanModule.tsx` | modified → committed (`339b7a4`) | both `chat` + `therapyPlan` catches |
| `frontend/src/features/report/__tests__/ReportModule.test.tsx` | modified → committed (`339b7a4`) | new regression case for `generate` 404 |
| `frontend/src/features/report/ReportModule.tsx` | modified (uncommitted) | wires `generateReport` catch through `isStaleSessionError` + `STALE_SESSION_TOAST` |
| `frontend/src/features/soap/SOAPModule.tsx` | modified (uncommitted) | `generateFromSession` 404 path |
| `frontend/src/features/soap/__tests__/SOAPModule.test.tsx` | modified (uncommitted) | SOAP 404 regression case |

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

Commit the four uncommitted follow-ups to `339b7a4` (`ReportModule.tsx`,
`SOAPModule.tsx`, `SOAPModule.test.tsx`, `stale-session.ts`) — suggested
message:
`feat(frontend): wire ReportModule and SOAPModule into stale-session helper`.
Then `git push` the five local commits (`129333c` + `cbf4d72` +
`11540d1` + `fc2cab1` + `339b7a4` + the new one) to `origin/main`.
After that, wait for the owner's anamnesis WIP to settle or pick the
next agent-safe item from `TASKS.md` "Next" column (UI loading
skeletons, PDF export quality, or backend test coverage for
therapy-plan / SOAP / compare — none touch the anamnesis files).

---

## Ideal Next Prompt

```text
Read docs/ai/HANDOFF.md, docs/ai/CURRENT.md, and docs/ai/PROJECT.md first.

Current situation: main is 5 commits ahead of origin/main (a3ba15a) —
129333c, cbf4d72, 11540d1, fc2cab1, 339b7a4 — the demo-mode +
onboarding follow-ups plus the stale-session 404 helper. Working tree
has four uncommitted follow-ups to 339b7a4 (ReportModule.tsx wiring,
SOAPModule.tsx + test, stale-session.ts refinement). 159/159 vitest +
tsc clean. The 2026-05-26 audit backlog is down to M-6 (anamnesis
completion logic), blocked on owner WIP in
backend/services/anamnesis_engine.py + phonological_analyzer.py — do
NOT touch those files until the owner explicitly hands them over.

Your task: <one of>
  (a) bundle the four uncommitted follow-ups into one commit, then push
      all six commits ahead of origin/main;
  (b) wait for the owner to hand off M-6;
  (c) pick the next agent-safe item from docs/ai/TASKS.md "Next" column
      (UI skeletons, PDF quality, or backend test coverage — none touch
      the anamnesis files);
  (d) <my custom direction>.

After completing the task, update docs/ai/CURRENT.md, docs/ai/TASKS.md, and
docs/ai/HANDOFF.md before stopping.
```

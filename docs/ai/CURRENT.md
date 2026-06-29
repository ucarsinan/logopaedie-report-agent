# CURRENT.md — Current Working State

> **This file must be updated at the end of every meaningful AI session.**
> It represents the live state of the work — not a backlog, not a history.
> If it is out of date, the next agent will start from wrong assumptions.

---

## Last Updated

- **Date:** 2026-06-29
- **Updated by:** Codex
- **Session focus:** Completed Git close-out for the AI handoff update and Vercel frontend proxy hardening. Committed and pushed `docs(ai): update workflow handoff for git close-out` plus `fix(frontend): default backend proxy to api on vercel`. Remaining unrelated backend, claim-copy, presentation, and manual-testing files are still intentionally unstaged.

---

## Current Goal

Reality-check status: **claim cleanup complete; synthetic smoke validation complete; small N2 cleanup complete; Vercel Preview local build path hardened**.

The MVP is consistently described as a portfolio/demo app using Groq directly for synthetic demo data. Local and public smoke checks confirm the demo shell is reachable and the report flow can be exercised with synthetic mocked backend data. Do not process real patient data through the current Groq/Vercel/Neon/Upstash setup.

The local dev servers used for the 2026-06-28 smoke were stopped before handoff.

The PowerPoint-style presentation PDF has been regenerated at `docs/mvp-presentation.pdf` after source claim cleanup.

**M-6** (anamnesis completion logic) still blocked on owner-driven WIP.

Vercel Preview deploy status: local `vercel build --yes` now passes with Preview settings. A real `vercel deploy` was **not** run because it changes external deployment state and needs explicit human approval.

Git close-out status: `main` was pushed to `origin/main` through commit `81ba9d2`. The first push attempt failed because the untracked proxy test remained visible while the matching unstaged implementation was hidden by the pre-push stash; this was fixed by committing the proxy implementation and test together.

---

## Current Branch

```text
main
```

Local `main` is in sync with `origin/main`.

---

## Verification snapshot

- `PROJECT_REALITY.md` created/updated with the 2026-06-26 audit.
- Public/presentation claim cleanup completed in README, landing components, `docs/qa-catalog.md`, and `scripts/generate_presentation.py`.
- `python3 scripts/generate_presentation.py` -> regenerated `docs/mvp-presentation.pdf`.
- PDF text check: **10 pages**; old phrases `100% DSGVO`, `AIProvider`, `LocalProvider`, and `voll funktionsfähig` no longer appear in extracted PDF text.
- PDF visual spot-check: rendered slide 10 with PyMuPDF; final compliance text is visible and framed as roadmap. `pdftoppm` was attempted but aborted because Fontconfig had no writable cache directory in the sandbox.
- `npm run lint -- src/components/landing/ArchitectureCallout.tsx src/components/landing/FeatureHighlights.tsx` -> passed.
- `git diff --check` -> passed.
- Full test suites were **not rerun** in the 2026-06-28 smoke session.
- Local backend `curl -i http://127.0.0.1:8001/livez` -> **200** `{"status":"alive"}`
- Local backend `curl -i http://127.0.0.1:8001/health` -> **401** `{"error":"unauthorized"}` (expected without service token)
- Local frontend `curl -I http://127.0.0.1:3001/` -> **200 OK**
- Local frontend `curl -I 'http://127.0.0.1:3001/module/report?demo=true'` -> **200 OK**
- Backend/PDF targeted tests:
  `cd backend && .venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_ops_hardening.py::test_livez_is_public_even_when_service_token_set tests/test_report_lifecycle.py::test_full_report_lifecycle tests/test_exports.py::test_download_pdf_returns_pdf_bytes tests/test_pdf_generator.py::TestGeneratePdf::test_returns_bytes`
  -> **4 passed in 2.61s**
- Browser smoke with Google Chrome headless against `http://127.0.0.1:3001` and mocked `/backend-api/*`:
  landing loaded, `module/report?demo=true` loaded, synthetic session created, `Befundbericht` selected, anamnesis marked complete, synthetic report generated, preview showed `Generierter Bericht`, `KI-generierter Entwurf`, `Patientendaten`, `Diagnose`, and `Drucken / PDF`. API calls were `GET /reports`, `POST /sessions`, `POST /sessions/aabbccddeeff/chat`, `POST /sessions/aabbccddeeff/generate`; no failed browser requests; only anonymous auth 401 console noise was ignored.
- Vercel public smoke:
  `https://logopaedie-report-agent.vercel.app/` -> **200**,
  `/api/livez` -> **200** `{"status":"alive"}`,
  `/api/health` -> **401** `{"error":"unauthorized"}` (expected without service token).
- N2 cleanup targeted tests:
  `cd backend && .venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_auth_middleware.py tests/test_access_token_blocklist.py tests/test_token_service.py tests/test_patient_service.py::test_derive_age_group_exactly_120_years_old_returns_erwachsen`
  -> **18 passed in 1.91s**
- N2 cleanup targeted lint:
  `cd backend && .venv/bin/ruff check dependencies.py services/access_token_blocklist.py services/token_service.py tests/test_access_token_blocklist.py tests/test_token_service.py tests/test_patient_service.py`
  -> **All checks passed**
- Vercel Preview investigation:
  `vercel ls logopaedie-report-agent --environment=preview` showed old Preview deploys from 32-33 days ago in Error state and older Preview deploys from 76+ days ago Ready.
- `vercel inspect https://logopaedie-report-agent-7ydsb0pag-sinan-ucars-projects.vercel.app --format=json` showed target `preview`, readyState `ERROR`, but the build record itself was `READY`; old build logs were no longer available.
- `vercel pull --yes --environment preview` downloaded Preview settings into ignored `.vercel/.env.preview.local`; secret values were not printed.
- `vercel build --yes` -> **Build completed successfully** for target `preview`.
- Frontend proxy targeted tests:
  `cd frontend && PATH=/Users/sinanucar/.nvm/versions/node/v22.12.0/bin:$PATH npm test -- --run src/app/_lib/backend-proxy.test.ts 'src/app/backend-api/[...path]/route.test.ts' 'src/app/auth-api/[...rest]/route.test.ts'`
  -> **3 test files passed, 8 tests passed**
- Frontend proxy targeted lint:
  `cd frontend && PATH=/Users/sinanucar/.nvm/versions/node/v22.12.0/bin:$PATH npx eslint src/app/_lib/backend-proxy.ts src/app/_lib/backend-proxy.test.ts`
  -> passed with no output.
- `python3 scripts/generate_presentation.py` → Successfully generated presentation PDF.
- `python3 -c "import PyPDF2; reader = PyPDF2.PdfReader('docs/mvp-presentation.pdf'); print(len(reader.pages))"` → **10** (exactly 10 pages).
- `ruff check .` → All checks passed!
- `pytest -q` → **533 passed, 9 skipped**
- Vercel production: `/api/livez` → 200, `/api/health` → 401 (correct), frontend → 200
- Git close-out check 2026-06-29:
  `./scripts/verify.sh` -> failed with exit 127 because `scripts/verify.sh` does not exist.
  `git diff --check` -> passed.
- Push verification 2026-06-29:
  Pre-push hook passed `backend · pytest`, `frontend · eslint`, and `frontend · vitest`; `git push` updated `origin/main` from `6fbe4c8` to `81ba9d2`.

---

## Key things the next agent should know

1. **Reality audit + claim cleanup 2026-06-26**:
   - Recommendation after cleanup: run a live synthetic-data smoke test before any feature work.
   - Biggest risk before this session was claims drift, not core app absence. That drift was corrected in README, landing copy, Q&A, presentation source, and regenerated PDF.
   - Actual backend still directly uses `GroqService`; Q&A now states that `AIProvider`/`LocalProvider` is not implemented in this repo and would be required for real patient-data use.
   - README and landing counters no longer use stale exact values like `157`/`59`/`35+`.
   - External check: GDPR Art. 9 treats health data as special-category data; Groq docs say retained customer data can be stored in US GCP buckets and ZDR is a configurable control. Therefore this repo remains demo/portfolio unless compliance architecture is changed and legally reviewed.

2. **Synthetic smoke validation 2026-06-28**:
   - Local backend/frontend were started in safe mode with SQLite, in-memory rate limiting, fake external credentials, and synthetic browser mocks for `/backend-api/*`.
   - The report UI path is validated only with synthetic mocked chat/generate responses; no real Groq chat/generate call was made.
   - Backend PDF export is validated by targeted tests/TestClient, not by clicking a real production PDF endpoint.
   - Vercel was checked only for public frontdoor/liveness/guard behavior. No mutating production flow was exercised.
   - The local Next SWC package was repaired again in `frontend/node_modules` by reinstalling `@next/swc-darwin-arm64@16.2.1 --no-save`; no tracked lockfile/source changed.

3. **Small N2 cleanup 2026-06-28**:
   - H-2 fixed: access-token revocation cutoff is now inclusive (`iat <= cutoff`) and covered by an equal-boundary test.
   - M-1 fixed: `TokenService.access_ttl_seconds` exposes the access TTL publicly; `dependencies.get_access_token_blocklist()` no longer reads `_access_ttl`.
   - M-3 fixed: the exactly-120-years-old age-group test no longer uses leap-year-fragile `date.replace(year=...)`.

4. **Vercel Preview hardening 2026-06-29**:
   - The old Preview deploy errors appear to be stale build/config failures from late May; the current local Preview build succeeds.
   - The remaining runtime risk was frontend BFF fallback: without `BACKEND_URL`, server-side proxies targeted `http://localhost:8001`, which is wrong on Vercel.
   - `frontend/src/app/_lib/backend-proxy.ts` now defaults to same-origin `/api` when `process.env.VERCEL` is set, while local development still defaults to `http://localhost:8001`.
   - A real Preview deployment was not run. That remains the final external verification step.

5. **Local dev server status from 2026-06-12**:
   - `http://127.0.0.1:3000` was already occupied by a different Next.js app (`Fil & Muz / BetriebsGehirn`), so this project's frontend was started on `http://127.0.0.1:3001`.
   - Backend was started on `http://127.0.0.1:8001` with `DATABASE_URL=sqlite:///./reports.local.db` and `RATE_LIMIT_REDIS_URL=memory://` to avoid running startup schema creation against the external Neon database.
   - The first frontend start failed because `node_modules/@next/swc-darwin-arm64` contained only a stub. The corrupt folder was moved to `/private/tmp/swc-darwin-arm64-stub-20260612`, then `npm install @next/swc-darwin-arm64@16.2.1 --no-save` restored `next-swc.darwin-arm64.node`.

6. **MVP Presentation PDF & Q&A Catalog exist, but copy needs validation**:
   - `docs/mvp-presentation.pdf` is generated and contains exactly 10 pages.
   - `docs/qa-catalog.md` contains a comprehensive German Q&A catalog (15 questions & answers) preparing the user for tech-stack, AI, and compliance queries.
   - Built using a custom ReportLab script `scripts/generate_presentation.py` with custom teal and navy slide formatting.
   - Slide 1 has a dark layout; slides 2-10 have a clean light-themed layout with breadcrumbs and container cards.

7. **Vercel production env vars are all set** (added 2026-06-03):
   - `TRUSTED_PROXY=vercel-edge` — satisfies boot guard; rate limiter
     falls back to socket IP (Vercel edge IP = shared bucket, acceptable for MVP)
   - `RATE_LIMIT_REDIS_URL=memory://` — Vercel's experimentalServices
     bundler does NOT include `redis` package at runtime; in-memory
     fallback is intentional for this deployment
   - `SERVICE_TOKEN`, `JWT_SECRET`, `SESSION_ENCRYPTION_KEY`,
     `PATIENT_ENCRYPTION_KEY` — all newly generated random values

8. **`EmailStr` is no longer from pydantic.** `routers/auth.py` defines
   a local `EmailStr = Annotated[str, AfterValidator(_check_email)]` with
   a simple regex. Reason: Vercel's experimentalServices vendoring does NOT
   bundle `email_validator` even when listed in requirements.txt or
   specified as `pydantic[email]` extra. The local type is functionally
   equivalent for input validation.

9. **`mypy` is now fully clean** (0 errors on all 72 source files).
   The alembic 0010/0011 errors are fixed: 0011's set comprehensions
   filter `None` explicitly; 0010's `Column` type uses `TypeEngine[Any]`.

10. **`SESSION_ENCRYPTION_KEY` added to `_set_env` autouse fixture** in
   `conftest.py`. Root cause: `get_totp_service()` is `@lru_cache(maxsize=1)`
   — its first call initializes the singleton. With N3's test additions
   changing collection order, `test_429_response_includes_retry_after_header`
   was the first to trigger it before any other test set the env var.

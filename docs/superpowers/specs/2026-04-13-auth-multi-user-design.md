# Multi-User Authentication — Design Spec

**Date:** 2026-04-13
**Project:** logopaedie-report-agent
**Scope:** Enterprise-grade multi-user auth (Email+Password, JWT with refresh rotation, 2FA TOTP, active sessions dashboard, audit log, admin role)
**Estimated effort:** 9–10 work sessions (~35–45h)

---

## 1. Goal & Context

Replace the current single-shared-`API_KEY` middleware ([backend/middleware/auth.py](../../../backend/middleware/auth.py)) with a real multi-user system. Each Logopäde gets an account; reports are owned by users; an admin role can audit and lock accounts.

This is a portfolio project — the goal is to demonstrate production-grade backend security skills (Argon2 hashing, JWT refresh-token rotation with reuse detection, TOTP, audit logging, rate limiting, session revocation) end-to-end across a Next.js + FastAPI stack.

### Non-goals

- Team/multi-tenant model (assistant accounts attached to a Logopäde) — separate spec later.
- OAuth (Google/GitHub) login.
- IP-to-geo lookup for sessions dashboard (DSGVO concerns, low demo value).
- Recovery codes for 2FA — admin manually disables 2FA via `/admin/users/{id}/disable-2fa`.
- E2E browser tests — separate spec if needed.

---

## 2. Architecture Overview

```
┌─────────────────┐   httpOnly cookies    ┌──────────────────┐
│  Next.js 16     │ ◄──────────────────►  │  FastAPI         │
│  - /login       │  access_token (15m)   │  /auth/* router  │
│  - /register    │  refresh_token (7d)   │  JWTAuthMW       │
│  - /verify      │                       │                  │
│  - /reset       │                       │  verifies JWT,   │
│  - /settings/   │                       │  injects user    │
│    security     │                       │  into request    │
│  - /admin/audit │                       │                  │
└─────────────────┘                       └────────┬─────────┘
        │                                          │
        │ AuthContext (React)                      ▼
        │ user, login(), logout()         ┌──────────────────┐
        ▼                                  │  Neon Postgres   │
   middleware.ts                           │  users           │
   (Next.js Edge):                         │  user_sessions   │
   redirects /login                        │  email_tokens    │
   if no cookie                            │  audit_log       │
                                           │  reports.user_id │
                                           └──────────────────┘
                                                    │
                                                    ▼
                                           ┌──────────────────┐
                                           │  Resend          │
                                           │  verify + reset  │
                                           └──────────────────┘
```

### Auth flow (login)

1. `POST /auth/login` with email+password → FastAPI verifies via Argon2, checks `email_verified=true`, optionally requires 2FA step.
2. Backend creates a `user_sessions` row (`refresh_token_hash`, `user_agent`, `ip`, `expires_at`), returns JWT access token + refresh cookie.
3. Next.js Route Handler `/api/auth/login` proxies to FastAPI and sets both cookies as `httpOnly`, `Secure`, `SameSite=Lax`.
4. Frontend `AuthContext` calls `/auth/me` and exposes the user.
5. On 401 from backend, frontend silently calls `/auth/refresh` and retries the request once. On refresh failure, redirects to `/login`.

### Logout flow

`POST /auth/logout` → backend revokes the `user_sessions` row → Next.js Route Handler clears cookies. Audit-log entry written.

### Why the Next.js Route Handler proxy

Cookies set directly by FastAPI work, but in production Vercel deploys frontend and backend on different subdomains → cross-site cookies need `SameSite=None; Secure`, which is brittle. Routing through `/api/auth/*` Route Handlers makes everything first-party (`SameSite=Lax`).

---

## 3. Data Model (Neon Postgres)

Four new tables and a column added to `reports`. UUID primary keys (no enumeration), refresh tokens stored as SHA-256 hashes, TOTP secrets Fernet-encrypted (reusing the same key as session-state encryption in Redis).

```python
# backend/models/auth.py

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, unique=True)            # lowercase, validated
    password_hash: str                                      # argon2id
    role: Literal["user", "admin"] = Field(default="user")
    email_verified: bool = Field(default=False)
    email_verified_at: datetime | None = None
    totp_secret: str | None = None                          # Fernet-encrypted
    totp_enabled: bool = Field(default=False)
    failed_login_count: int = Field(default=0)
    locked_until: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    refresh_token_hash: str = Field(index=True)             # sha256 of token
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    last_used_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime                                     # +7d
    revoked_at: datetime | None = None

class EmailToken(SQLModel, table=True):
    __tablename__ = "email_tokens"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(index=True)                      # sha256
    purpose: Literal["verify_email", "reset_password"]
    expires_at: datetime                                     # verify: 24h, reset: 1h
    used_at: datetime | None = None

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID | None = Field(foreign_key="users.id", index=True)
    event: str = Field(index=True)
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow, index=True)
```

```python
# backend/models/report.py — extended
class Report(SQLModel, table=True):
    # ... existing fields ...
    user_id: UUID = Field(foreign_key="users.id", index=True)  # NOT NULL after migration
```

### Indexes

`users.email`, `user_sessions.refresh_token_hash`, `user_sessions.user_id`, `email_tokens.token_hash`, `audit_log.user_id`, `audit_log.created_at`, `reports.user_id`.

### Design rationale

- **One `email_tokens` table for verify+reset** — same shape, distinguished by `purpose`. YAGNI: no need for two tables.
- **`failed_login_count` + `locked_until` on the user row** — simpler than a separate Redis counter; lockouts are rare.
- **`audit_log.metadata` as JSON** — flexible per-event payload without schema migrations.
- **Token hashes only** — DB leak does not expose usable tokens.

---

## 4. Backend Structure (FastAPI)

### New files

```
backend/
├── models/auth.py                 # User, UserSession, EmailToken, AuditLog
├── services/
│   ├── auth_service.py            # register, login, refresh, logout, lockout
│   ├── password_service.py        # argon2 hash + verify (passlib[argon2])
│   ├── token_service.py           # JWT encode/decode, refresh token gen/hash
│   ├── totp_service.py            # pyotp wrapper
│   ├── email_service.py           # Resend client + console fallback
│   └── audit_service.py           # log_event(...)
├── routers/
│   ├── auth.py                    # /auth/* endpoints
│   └── auth_admin.py              # /admin/* endpoints
├── middleware/
│   ├── auth.py                    # REPLACED: JWT verify (was API_KEY)
│   └── service_token.py           # NEW: narrow SERVICE_TOKEN path for /health + cron
├── dependencies.py                # extended: get_current_user, get_admin_user
├── exceptions.py                  # extended: AuthError hierarchy
└── alembic/                       # NEW: migrations
```

### Endpoints (all under `/api/auth`)

```
POST   /auth/register              { email, password }
                                   → 201, sends verify mail, NO auto-login
POST   /auth/verify-email          { token }                        → 200
POST   /auth/resend-verification   { email }                        → 200 (always)
POST   /auth/login                 { email, password }
                                   → 200 + cookies, OR 200 { totp_required, challenge_id }
POST   /auth/login/2fa             { challenge_id, code }           → 200 + cookies
POST   /auth/refresh               (refresh_token cookie)           → 200 + new cookies (rotation)
POST   /auth/logout                → 200, revokes current session
GET    /auth/me                    → user profile

POST   /auth/password/reset/request { email }                       → 200 (always)
POST   /auth/password/reset/confirm { token, new_password }
                                   → 200, revokes ALL sessions
POST   /auth/password/change       { old_password, new_password }
                                   → 200, revokes other sessions

GET    /auth/sessions              → active sessions list
DELETE /auth/sessions/{id}         → revoke one session

POST   /auth/2fa/setup             → { secret, qr_uri }  (totp_enabled=false)
POST   /auth/2fa/enable            { code }                         → totp_enabled=true
POST   /auth/2fa/disable           { password, code }               → totp_enabled=false

GET    /admin/audit                → paginated audit log (admin only)
POST   /admin/users/{id}/lock      → admin only
POST   /admin/users/{id}/unlock    → admin only
POST   /admin/users/{id}/disable-2fa → admin only (recovery path for lost-phone)
```

### Middleware order (in `main.py`)

```python
app.add_middleware(CORSMiddleware, ...)        # existing
app.add_middleware(ServiceTokenMiddleware)     # NEW: X-Service-Token only for /health, /cron/*
app.add_middleware(JWTAuthMiddleware)          # NEW: extract user from access_token cookie → request.state.user
```

`JWTAuthMiddleware` sets `request.state.user` to `User | None` and never raises 401 itself. Routes decide via dependency:

- `get_current_user` → 401 if no user
- `get_optional_user` → returns `None` (e.g. for `/auth/login`, `/health`)
- `get_admin_user` → 403 if not admin

### Rate limits (slowapi, new)

- `/auth/login`, `/auth/login/2fa`: **5/min/IP** + per-user `failed_login_count` lockout (10 fails → 15 min lockout)
- `/auth/register`: **3/min/IP**
- `/auth/password/reset/request`: **3/h/IP**
- `/auth/refresh`: **30/min/IP**

### Exception hierarchy (added to `exceptions.py`)

```python
class AuthError(LogopaedieError): ...                   # 401 default
class InvalidCredentialsError(AuthError): ...           # 401, generic message
class EmailNotVerifiedError(AuthError): ...             # 403
class TwoFactorRequiredError(AuthError): ...            # special: returns 200 with challenge_id
class AccountLockedError(AuthError): ...                # 423
class InvalidTokenError(AuthError): ...                 # 401
class TokenExpiredError(AuthError): ...                 # 401
class InsufficientPermissionsError(AuthError): ...      # 403
```

### Security invariants

- Login response is **always** generic: `"Email or password incorrect"` — no user enumeration.
- Register / password-reset-request **always** return 200 even if email does not exist.
- **Refresh token rotation:** old refresh is invalidated, new one issued. **Reuse detection:** if an already-used refresh token is presented, revoke ALL the user's sessions and write `session.refresh_reuse_detected` audit event.
- Password reset and 2FA disable revoke ALL sessions.

### Existing code touched

- [backend/middleware/auth.py](../../../backend/middleware/auth.py) → replaced (API_KEY logic removed).
- `backend/routers/reports.py` → all endpoints filter by `current_user.id`.
- `backend/routers/sessions.py` → session creation stores `user_id`; `GET /sessions/{id}` checks ownership.

---

## 5. Frontend Structure (Next.js 16)

Follows the existing `features/` modular architecture.

### New files

```
frontend/src/
├── app/
│   ├── (auth)/                          # route group, centered layout, no header
│   │   ├── layout.tsx
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   ├── verify-email/page.tsx        # ?token=...
│   │   ├── forgot-password/page.tsx
│   │   └── reset-password/page.tsx      # ?token=...
│   ├── settings/security/page.tsx       # password, 2FA, active sessions
│   ├── admin/audit/page.tsx             # audit log viewer (admin only)
│   └── api/auth/
│       ├── login/route.ts               # proxy to FastAPI, sets httpOnly cookies
│       ├── logout/route.ts              # proxy + cookie clear
│       ├── refresh/route.ts             # silent refresh
│       └── [...rest]/route.ts           # generic catch-all
├── features/auth/
│   ├── components/
│   │   ├── LoginForm.tsx
│   │   ├── RegisterForm.tsx
│   │   ├── TwoFactorChallenge.tsx
│   │   ├── PasswordStrengthMeter.tsx    # @zxcvbn-ts/core
│   │   ├── ActiveSessionsList.tsx
│   │   ├── TwoFactorSetup.tsx           # QR + initial-code verify
│   │   └── AuditLogTable.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useLogin.ts
│   │   ├── useRegister.ts
│   │   └── useActiveSessions.ts
│   ├── api.ts                           # typed /auth/* calls
│   └── types.ts                         # User, Session, AuthState
├── providers/AuthProvider.tsx           # context, loads /auth/me on mount
├── middleware.ts                        # NEW: edge middleware → /login redirect if no cookie
└── lib/api.ts                           # EXTENDED: 401 → silent /auth/refresh → retry
```

### AuthProvider state

```ts
type AuthState =
  | { status: "loading" }
  | { status: "authenticated"; user: User }
  | { status: "unauthenticated" };
```

Exposes `state, login(email,pw), logout(), refresh()`. Wraps the app in `app/layout.tsx`.

### Edge middleware

```ts
const PROTECTED  = ["/", "/sessions", "/reports", "/settings", "/admin"];
const ADMIN_ONLY = ["/admin"];
const PUBLIC     = ["/login", "/register", "/verify-email", "/forgot-password", "/reset-password"];
```

Logic:

- Has `access_token` cookie → pass through.
- Only `refresh_token` cookie → pass through, client triggers silent refresh.
- No cookie + protected route → redirect to `/login?next=<path>`.
- Authenticated + on `/login` → redirect to `/`.

Edge middleware **cannot** verify the JWT (no secret available). It only checks for cookie presence — security is enforced by the backend on every API call. The middleware is purely a UX gate to avoid a flash of unauthenticated content.

### API client 401 handling (`lib/api.ts`)

```ts
async function apiCall(url, opts) {
  const res = await fetch(url, opts);
  if (res.status === 401 && !url.includes("/auth/")) {
    const refreshed = await fetch("/api/auth/refresh", { method: "POST" });
    if (refreshed.ok) return fetch(url, opts);  // retry once
    window.location.href = "/login";
  }
  return res;
}
```

Single-flight: parallel 401s share **one** in-flight refresh promise.

### UX details

- **Login** — email + password + "Forgot password?" link. On 2FA-required: second step renders inline (no page change).
- **Register** — email + password + `PasswordStrengthMeter` (zxcvbn-ts, ~12kb). After submit: "Check your email" — no auto-login.
- **Verify-email** — reads `?token=`, calls backend, shows success.
- **Settings/Security** — three cards: change password, 2FA setup with QR code, active sessions list (UA + IP + per-row revoke button, current session marked).
- **Admin/Audit** — table with filter by `event` and `user_id`, offset pagination.

### Existing code touched

- `frontend/src/app/layout.tsx` — wrapped with `<AuthProvider>`.
- `frontend/src/lib/api.ts` — 401 interceptor + single-flight refresh.

---

## 6. Email Flows (Resend)

### Setup

- Package: `resend` (Python SDK).
- Env: `RESEND_API_KEY`, `EMAIL_FROM`, `APP_URL`.
- Resend domain verification needed for production. For local dev: when `RESEND_API_KEY` is unset, `EmailService` falls back to `console` mode — logs the email body to stdout. No provider account needed for local testing.
- Templates are inline plain-text Python strings (no React Email — YAGNI for two emails).

### Verify flow

```
1. POST /auth/register {email, password}
2. AuthService:
   - lowercase + validate email
   - if user already exists → return 200 (no enumeration), do NOT send mail (spam vector)
   - hash password (argon2id)
   - INSERT users (email_verified=false)
   - token = secrets.token_urlsafe(32)
   - INSERT email_tokens (purpose="verify_email", token_hash=sha256(token), expires_at=+24h)
   - EmailService.send_verify(email, f"{APP_URL}/verify-email?token={token}")
   - audit: "user.register"
3. → 201 {message: "Check your email"}

4. User clicks link → frontend /verify-email?token=...
5. Frontend POST /auth/verify-email {token}
6. AuthService.verify_email:
   - lookup email_tokens WHERE token_hash=sha256(token) AND purpose="verify_email"
   - check: not used, not expired
   - UPDATE users SET email_verified=true
   - UPDATE email_tokens SET used_at=now()
   - audit: "user.email_verified"
7. → 200
```

`POST /auth/login` rejects with `EmailNotVerifiedError` (403) if `email_verified=false`. Frontend offers a "resend verification" button → `POST /auth/resend-verification` (rate-limited 1/min/email).

### Reset flow

```
1. POST /auth/password/reset/request {email}
2. AuthService:
   - lookup user; if not found → return 200, no mail
   - if found: generate token, INSERT email_tokens (purpose="reset_password", expires_at=+1h)
   - EmailService.send_reset(...)
   - audit: "password.reset_requested"
3. → 200 (always, generic)

4. User clicks → /reset-password?token=...
5. Frontend POST /auth/password/reset/confirm {token, new_password}
6. AuthService.reset_password:
   - validate token
   - UPDATE users SET password_hash=argon2(new_password)
   - UPDATE email_tokens SET used_at=now()
   - DELETE FROM user_sessions WHERE user_id=user.id  -- revoke ALL sessions
   - audit: "password.reset_completed"
7. → 200
```

### Token storage

Tokens are stored only as SHA-256 hashes. Plaintext goes out by email once and is never readable from the DB. Single-use via `used_at`.

---

## 7. 2FA, Sessions Dashboard, Audit Log

### 7.1 2FA (TOTP, opt-in)

Library: `pyotp` + `qrcode.react` for client-side QR rendering (no backend image roundtrip).

**Setup flow** (`/settings/security`):

```
1. POST /auth/2fa/setup
   - secret = pyotp.random_base32()
   - encrypt with Fernet (same key as Redis session encryption)
   - UPDATE users SET totp_secret=<encrypted>, totp_enabled=false  (NOT enabled yet!)
   - return { secret_plain, qr_uri }
     qr_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="Logopädie Report Agent")
2. Frontend renders QR + shows secret as fallback string
3. User scans, app shows 6-digit code
4. POST /auth/2fa/enable {code}
5. Backend: pyotp.TOTP(decrypt(secret)).verify(code, valid_window=1)
   - on success: UPDATE users SET totp_enabled=true
   - audit: "2fa.enable"
   - revoke all OTHER sessions
```

The two-step (setup → enable) prevents lockout if the user scans the QR but never confirms (wrong app, abandoned).

**Login with 2FA:**

```
1. POST /auth/login {email, password}
2. Credentials valid + totp_enabled=true:
   - challenge_id = secrets.token_urlsafe(16)
   - cache in Redis: "2fa_challenge:<id>" → user_id, TTL 5 min
   - return 200 { totp_required: true, challenge_id }   -- NO cookies
3. Frontend renders inline 6-digit input
4. POST /auth/login/2fa {challenge_id, code}
5. Backend:
   - lookup challenge; expired/missing → 401
   - verify TOTP code (valid_window=1, ±30s drift)
   - on fail: failed_login_count++, possibly lockout
   - on success: delete challenge, create session, set cookies, audit "login.success"
```

**Disable:** `POST /auth/2fa/disable {password, code}` requires **both** current password AND current TOTP code — prevents abuse via leaked session cookie.

**Recovery:** No recovery codes (out of scope). Lost-phone case: admin calls `POST /admin/users/{id}/disable-2fa`.

### 7.2 Active sessions dashboard

UI in `/settings/security`. Shows current session marked, plus other sessions with UA, IP, last-active, individual "revoke" button, and a "revoke all other devices" action.

**Backend:**

```
GET /auth/sessions
→ SELECT * FROM user_sessions
   WHERE user_id=current AND revoked_at IS NULL AND expires_at > now()
   ORDER BY last_used_at DESC
→ marks the current session via match on refresh_token_hash from cookie

DELETE /auth/sessions/{id}
→ UPDATE user_sessions SET revoked_at=now() WHERE id=? AND user_id=current
→ audit "session.revoke" with metadata={revoked_session_id}
→ if current session was revoked: clear cookies, frontend redirects /login
```

UA parsing via `user-agents` Python lib. **No IP-to-geo** (DSGVO + low value). `last_used_at` updated on every successful `/auth/refresh` (every 15 min, no perf concern).

### 7.3 Audit log

Logged events (each: `user_id`, `event`, `ip`, `user_agent`, `metadata`, `created_at`):

```
user.register                  metadata: {email}
user.email_verified
login.success
login.fail                     metadata: {reason: "bad_password" | "not_verified" | "locked"}
login.2fa_required
login.2fa_success
login.2fa_fail
logout                         metadata: {session_id}
session.revoke                 metadata: {revoked_session_id, by: "user" | "admin"}
session.refresh_reuse_detected metadata: {session_id}   -- SECURITY-CRITICAL
password.change
password.reset_requested
password.reset_completed
2fa.enable
2fa.disable
admin.user_lock                metadata: {target_user_id}
admin.user_unlock              metadata: {target_user_id}
admin.2fa_disable              metadata: {target_user_id}
```

**Synchronous logging** via `AuditService.log(...)` from routes/services. DB insert is <5ms; if logging fails, the auth flow fails (fail-closed). No background worker.

**Admin viewer** (`/admin/audit`): table with filters by `event` and `user_id`, offset pagination via `GET /admin/audit?event=...&user_id=...&limit=50&offset=0`.

**Retention:** none (audit logs grow slowly; Neon free tier handles years).

---

## 8. Migrations, Testing, Roll-out

### 8.1 Database migrations

**Alembic is introduced** as part of this work (the project currently uses `SQLModel.metadata.create_all`).

```
backend/alembic/
├── env.py
└── versions/
    ├── 0001_initial_reports_baseline.py     # baseline from existing schema
    ├── 0002_auth_tables.py                  # users, user_sessions, email_tokens, audit_log
    └── 0003_reports_user_id.py              # delete existing rows, add user_id NOT NULL
```

**Migration 0003 is destructive** (existing reports are deleted — confirmed acceptable for portfolio demo):

```python
def upgrade():
    op.execute("DELETE FROM reports")
    op.add_column("reports", sa.Column("user_id", UUID, nullable=False))
    op.create_foreign_key("fk_reports_user", "reports", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_reports_user_id", "reports", ["user_id"])
```

Existing Redis-stored anamnese sessions remain untouched (24h TTL — they expire naturally; new ones store `user_id`).

### 8.2 Roll-out order

1. Run migration 0002 — create new tables, no impact on existing.
2. Run migration 0003 — drop reports, add `user_id`.
3. Deploy backend — new auth routes, new middleware.
4. Deploy frontend — login pages, edge middleware.

On Vercel's monorepo deploy, steps 3 + 4 are atomic. The brief window where backend is "broken" for a stale frontend is acceptable for a demo.

### 8.3 Testing

**Backend (pytest, added to existing 35 tests):**

```
backend/tests/auth/
├── test_password_service.py
├── test_token_service.py            # JWT encode/decode/expiry/tampering
├── test_totp_service.py             # generate, verify, valid_window, drift
├── test_auth_service.py             # register, login, lockout, refresh-rotation
├── test_email_service.py            # console mode, template render
├── test_audit_service.py
├── test_routes_auth.py              # all /auth/* happy + error paths
├── test_routes_auth_admin.py        # /admin/* with + without admin role
├── test_middleware_jwt.py
└── test_security.py                 # SECURITY-CRITICAL:
                                     #   - User enumeration: all endpoints generic
                                     #   - Refresh-token reuse detection revokes all
                                     #   - Password reset revokes all sessions
                                     #   - Login lockout after 10 fails
                                     #   - 2FA disable requires password+code
                                     #   - Token tampering rejected
                                     #   - Audit log written for critical events
backend/tests/test_reports_ownership.py  # User A cannot see User B's reports
```

**Test DB:** SQLite in-memory (existing pattern). The `audit_log.metadata` JSON column requires SQLite ≥3.38; if that's not available in the test environment, fall back to `Text` with manual JSON encode.

**Email in tests:** `EmailService` injected via dependency, replaced with `FakeEmailService` that records sent emails into a list for assertion.

**Frontend (vitest):**

```
frontend/src/features/auth/
├── components/__tests__/
│   ├── LoginForm.test.tsx
│   ├── RegisterForm.test.tsx
│   └── ActiveSessionsList.test.tsx
├── hooks/__tests__/useAuth.test.tsx
└── api.test.ts
```

**E2E:** out of scope.

### 8.4 Implementation phases

| Phase | Scope | Sessions |
|---|---|---|
| 1 | Alembic + 4 auth tables + SQLModel classes | 1 |
| 2 | Core services (Password, Token, Totp, Audit, Email-console) | 1 |
| 3 | Auth routes without 2FA: register, verify, login, logout, refresh, /me, reset | 1 |
| 4 | 2FA: setup, enable, disable, login/2fa | 1 |
| 5 | Sessions dashboard + admin audit + admin lock/unlock | 1 |
| 6 | Secure existing routes + reports `user_id` migration (0003) | 1 |
| 7 | Frontend AuthProvider + middleware + API proxy + 401 interceptor | 1 |
| 8 | Frontend auth pages (login, register, verify, forgot, reset) | 1 |
| 9 | Frontend settings/security + admin/audit | 1 |
| 10 | Polish: Resend domain verify, env vars, README, Vercel envs | 0.5 |

**Total: 9.5 sessions, ~35–45h.**

### 8.5 New dependencies

**Backend:**

- `passlib[argon2]` — password hashing
- `pyjwt` — JWT encode/decode
- `pyotp` — TOTP
- `resend` — email
- `user-agents` — UA parsing
- `alembic` — migrations

**Frontend:**

- `qrcode.react` — client-side QR rendering
- `@zxcvbn-ts/core` + `@zxcvbn-ts/language-en` — password strength meter

### 8.6 New env vars

```bash
# Auth
JWT_SECRET=                    # 32 random bytes
JWT_ALGORITHM=HS256
ACCESS_TOKEN_TTL_MINUTES=15
REFRESH_TOKEN_TTL_DAYS=7

# Email (Resend)
RESEND_API_KEY=                # empty = console fallback
EMAIL_FROM=noreply@<domain>
APP_URL=http://localhost:3000  # used in mail links

# Service token (for /health, cron)
SERVICE_TOKEN=                 # replaces old API_KEY
```

The old `API_KEY` env var is removed.

---

## 9. Open questions resolved during brainstorming

| # | Question | Decision |
|---|---|---|
| 1 | Auth scope | B — multi-user with email+password |
| 2 | Where auth lives | B — FastAPI-owned (Python JWT, Argon2, etc.) |
| 3 | Token strategy | B — access + refresh, both httpOnly cookies, refresh sessions in Neon |
| 4 | Feature scope | C — Enterprise (verify, reset, 2FA, sessions dashboard, audit log) |
| 4a | Existing reports | (i) delete all via migration 0003 |
| 4b | API_KEY middleware | Replace; keep narrow `SERVICE_TOKEN` path for `/health` + cron |
| 5 | Role model | B — user + admin (admin set manually via DB flag) |
| 6a | 2FA | (i) opt-in |
| 6b | Email provider | (i) Resend with console fallback |
| 6c | Frontend UX | (i) dedicated routes |
| 6d | Password policy | (i) min 12 characters, no complexity rules (NIST 2024) |

# Auth Multi-User Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single shared-API-key gate with a production-grade multi-user authentication system (register, verify, login/logout, password reset, optional TOTP 2FA, active-session dashboard, audit log, admin controls) owned entirely by the FastAPI backend, with first-party cookies set through a Next.js Route Handler proxy.

**Architecture:** FastAPI owns auth state (SQLModel tables on Neon Postgres, Alembic migrations, argon2id password hashes, short-lived JWT access tokens + rotating opaque refresh tokens with reuse-detection, slowapi rate limiting, Fernet-encrypted TOTP secrets). Next.js 16 App Router handles UX through a `(auth)` route group and proxies all `/api/auth/*` calls via server-side Route Handlers so cookies stay `SameSite=Lax` first-party. Edge middleware gates protected routes on cookie presence only. A single-flight 401 interceptor in the client handles transparent refresh.

**Tech Stack:** Python 3.12, FastAPI, SQLModel, Alembic, Neon Postgres, Upstash Redis (2FA challenge store + slowapi backend), passlib[argon2], pyjwt, pyotp, resend, user-agents. Next.js 16, React 19, Tailwind CSS v4, TypeScript, Vitest + Testing Library, `@zxcvbn-ts/core`, `qrcode.react`.

**Security review strategy:** At each security-critical phase boundary, a dedicated task dispatches an **Opus subagent** (`model: "opus"`) to review the code before moving on. The main implementation session can stay on Sonnet; Opus is only pulled in for the 6 gates (2A, 3A, 4A, 6A, 7A, 8A) where subtle auth bugs tend to hide.

---

## Phase 1: Alembic Baseline + Auth Tables

**Goal:** Introduce Alembic migrations and create the 4 new auth tables (`users`, `user_sessions`, `email_tokens`, `audit_log`) plus SQLModel classes.

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial_reports_baseline.py`
- Create: `backend/alembic/versions/0002_auth_tables.py`
- Create: `backend/models/auth.py`
- Modify: `backend/database.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/test_auth_models.py`
- Test: `backend/tests/test_alembic_migrations.py`

---

### Task 1.1: Add alembic dependency and SQLModel auth models

- [ ] **Step 1: Write the failing test**

  File: `backend/tests/test_auth_models.py`

  ```python
  """Schema-only tests for auth SQLModel classes."""
  from datetime import datetime, timedelta, timezone
  from uuid import UUID, uuid4

  import pytest
  from sqlalchemy.exc import IntegrityError
  from sqlmodel import Session, SQLModel, create_engine, select

  from models.auth import AuditLog, EmailToken, User, UserSession


  @pytest.fixture
  def engine():
      eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
      SQLModel.metadata.create_all(eng)
      yield eng
      SQLModel.metadata.drop_all(eng)


  def test_auth_models_create_all(engine):
      table_names = set(SQLModel.metadata.tables.keys())
      assert {"users", "user_sessions", "email_tokens", "audit_log"} <= table_names


  def test_user_email_unique_constraint(engine):
      with Session(engine) as db:
          db.add(User(email="a@example.com", password_hash="x"))
          db.commit()
          db.add(User(email="a@example.com", password_hash="y"))
          with pytest.raises(IntegrityError):
              db.commit()


  def test_user_default_role_and_flags(engine):
      with Session(engine) as db:
          u = User(email="b@example.com", password_hash="x")
          db.add(u)
          db.commit()
          db.refresh(u)
          assert u.role == "user"
          assert u.email_verified is False
          assert u.totp_enabled is False
          assert u.failed_login_count == 0
          assert isinstance(u.id, UUID)


  def test_audit_log_metadata_json_roundtrip(engine):
      with Session(engine) as db:
          entry = AuditLog(
              user_id=None,
              event="login.fail",
              ip_address="127.0.0.1",
              user_agent="pytest",
              metadata_json={"reason": "bad_password", "attempt": 3},
          )
          db.add(entry)
          db.commit()
          row = db.exec(select(AuditLog)).one()
          assert row.metadata_json == {"reason": "bad_password", "attempt": 3}


  def test_user_sessions_indexes_present(engine):
      table = SQLModel.metadata.tables["user_sessions"]
      indexed = {col.name for col in table.columns if col.index}
      assert "user_id" in indexed
      assert "refresh_token_hash" in indexed


  def test_email_token_purpose_and_expiry(engine):
      with Session(engine) as db:
          user = User(email="c@example.com", password_hash="x")
          db.add(user)
          db.commit()
          db.refresh(user)
          tok = EmailToken(
              user_id=user.id,
              token_hash="deadbeef",
              purpose="verify_email",
              expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
          )
          db.add(tok)
          db.commit()
          db.refresh(tok)
          assert tok.purpose == "verify_email"
          assert tok.used_at is None


  def test_user_session_has_revoked_at_nullable(engine):
      with Session(engine) as db:
          user = User(email="d@example.com", password_hash="x")
          db.add(user)
          db.commit()
          db.refresh(user)
          sess = UserSession(
              user_id=user.id,
              refresh_token_hash="hash",
              expires_at=datetime.now(timezone.utc) + timedelta(days=7),
          )
          db.add(sess)
          db.commit()
          db.refresh(sess)
          assert sess.revoked_at is None
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd backend && python -m pytest tests/test_auth_models.py -v`
  Expected: FAIL with `ModuleNotFoundError: No module named 'models.auth'`

- [ ] **Step 3: Implement**

  File: `backend/models/auth.py`

  ```python
  """SQLModel tables for multi-user authentication."""
  from __future__ import annotations

  from datetime import datetime, timezone
  from typing import Literal
  from uuid import UUID, uuid4

  from sqlalchemy import CHAR, Column, DateTime, ForeignKey
  from sqlalchemy.dialects.postgresql import UUID as PG_UUID
  from sqlmodel import JSON, Field, SQLModel

  _UUID_TYPE = PG_UUID(as_uuid=True).with_variant(CHAR(36), "sqlite")


  def _utcnow() -> datetime:
      return datetime.now(timezone.utc)


  class User(SQLModel, table=True):
      __tablename__ = "users"

      id: UUID = Field(default_factory=uuid4, primary_key=True)
      email: str = Field(index=True, unique=True)
      password_hash: str
      role: Literal["user", "admin"] = Field(default="user")
      email_verified: bool = Field(default=False)
      email_verified_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
      totp_secret: str | None = Field(default=None)
      totp_enabled: bool = Field(default=False)
      failed_login_count: int = Field(default=0)
      locked_until: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
      created_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
      updated_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))


  class UserSession(SQLModel, table=True):
      __tablename__ = "user_sessions"

      id: UUID = Field(default_factory=uuid4, primary_key=True)
      user_id: UUID = Field(
          sa_column=Column(_UUID_TYPE, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
      )
      refresh_token_hash: str = Field(index=True)
      user_agent: str | None = Field(default=None)
      ip_address: str | None = Field(default=None)
      created_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
      last_used_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
      expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
      revoked_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))


  class EmailToken(SQLModel, table=True):
      __tablename__ = "email_tokens"

      id: UUID = Field(default_factory=uuid4, primary_key=True)
      user_id: UUID = Field(
          sa_column=Column(_UUID_TYPE, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
      )
      token_hash: str = Field(index=True)
      purpose: Literal["verify_email", "reset_password"]
      expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
      used_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))


  class AuditLog(SQLModel, table=True):
      __tablename__ = "audit_log"

      id: UUID = Field(default_factory=uuid4, primary_key=True)
      user_id: UUID | None = Field(
          default=None,
          sa_column=Column(_UUID_TYPE, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
      )
      event: str = Field(index=True)
      ip_address: str | None = Field(default=None)
      user_agent: str | None = Field(default=None)
      metadata_json: dict = Field(default_factory=dict, sa_column=Column("metadata_json", JSON, nullable=False))
      created_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False, index=True))
  ```

  Modify `backend/pyproject.toml` — add `"alembic>=1.13"` to the `[project].dependencies` list.

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd backend && python -m pytest tests/test_auth_models.py -v`
  Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

  ```bash
  git add backend/models/auth.py backend/tests/test_auth_models.py backend/pyproject.toml
  git commit -m "feat(auth): add SQLModel classes for users, sessions, email_tokens, audit_log"
  ```

---

### Task 1.2: Alembic baseline migration (reports-only)

- [ ] **Step 1: Write the failing test**

  File: `backend/tests/test_alembic_migrations.py`

  ```python
  """Alembic upgrade/downgrade smoke tests."""
  import os
  import tempfile
  from pathlib import Path

  import pytest
  from alembic import command
  from alembic.config import Config
  from sqlalchemy import create_engine, inspect

  BACKEND_DIR = Path(__file__).resolve().parent.parent


  @pytest.fixture
  def alembic_cfg():
      tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
      tmp.close()
      url = f"sqlite:///{tmp.name}"
      cfg = Config(str(BACKEND_DIR / "alembic.ini"))
      cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
      cfg.set_main_option("sqlalchemy.url", url)
      yield cfg, url
      os.unlink(tmp.name)


  def test_alembic_upgrade_baseline(alembic_cfg):
      cfg, url = alembic_cfg
      command.upgrade(cfg, "0001")
      insp = inspect(create_engine(url))
      assert "reports" in insp.get_table_names()
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd backend && python -m pytest tests/test_alembic_migrations.py::test_alembic_upgrade_baseline -v`
  Expected: FAIL with `FileNotFoundError` or `alembic.util.exc.CommandError` (no alembic.ini)

- [ ] **Step 3: Implement**

  File: `backend/alembic.ini`

  ```ini
  [alembic]
  script_location = alembic
  prepend_sys_path = .
  sqlalchemy.url = driver://user:pass@localhost/dbname

  [loggers]
  keys = root,sqlalchemy,alembic

  [handlers]
  keys = console

  [formatters]
  keys = generic

  [logger_root]
  level = WARN
  handlers = console
  qualname =

  [logger_sqlalchemy]
  level = WARN
  handlers =
  qualname = sqlalchemy.engine

  [logger_alembic]
  level = INFO
  handlers =
  qualname = alembic

  [handler_console]
  class = StreamHandler
  args = (sys.stderr,)
  level = NOTSET
  formatter = generic

  [formatter_generic]
  format = %(levelname)-5.5s [%(name)s] %(message)s
  datefmt = %H:%M:%S
  ```

  File: `backend/alembic/env.py`

  ```python
  """Alembic environment for logopaedie-report-agent backend."""
  import os
  import sys
  from logging.config import fileConfig
  from pathlib import Path

  from alembic import context
  from sqlalchemy import engine_from_config, pool

  BACKEND_DIR = Path(__file__).resolve().parent.parent
  sys.path.insert(0, str(BACKEND_DIR))

  from sqlmodel import SQLModel  # noqa: E402

  import models.auth  # noqa: F401,E402
  try:
      import models.report  # noqa: F401,E402
  except ImportError:
      pass

  config = context.config
  if config.config_file_name is not None:
      fileConfig(config.config_file_name)

  db_url = os.getenv("DATABASE_URL")
  if db_url:
      config.set_main_option("sqlalchemy.url", db_url)

  target_metadata = SQLModel.metadata


  def run_migrations_offline() -> None:
      url = config.get_main_option("sqlalchemy.url")
      context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                        dialect_opts={"paramstyle": "named"})
      with context.begin_transaction():
          context.run_migrations()


  def run_migrations_online() -> None:
      connectable = engine_from_config(
          config.get_section(config.config_ini_section, {}),
          prefix="sqlalchemy.",
          poolclass=pool.NullPool,
      )
      with connectable.connect() as connection:
          context.configure(connection=connection, target_metadata=target_metadata)
          with context.begin_transaction():
              context.run_migrations()


  if context.is_offline_mode():
      run_migrations_offline()
  else:
      run_migrations_online()
  ```

  File: `backend/alembic/versions/0001_initial_reports_baseline.py`

  ```python
  """initial reports baseline

  Revision ID: 0001
  Revises:
  Create Date: 2026-04-13
  """
  from __future__ import annotations

  import sqlalchemy as sa
  from alembic import op

  revision = "0001"
  down_revision = None
  branch_labels = None
  depends_on = None


  def upgrade() -> None:
      op.create_table(
          "reports",
          sa.Column("id", sa.String(length=36), primary_key=True),
          sa.Column("report_type", sa.String(), nullable=False),
          sa.Column("content", sa.Text(), nullable=False),
          sa.Column("patient_name", sa.String(), nullable=True),
          sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
      )
      op.create_index("ix_reports_created_at", "reports", ["created_at"])


  def downgrade() -> None:
      op.drop_index("ix_reports_created_at", table_name="reports")
      op.drop_table("reports")
  ```

  Create empty file: `backend/alembic/versions/__init__.py` (touch).

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd backend && python -m pytest tests/test_alembic_migrations.py::test_alembic_upgrade_baseline -v`
  Expected: PASS

- [ ] **Step 5: Commit**

  ```bash
  git add backend/alembic.ini backend/alembic/env.py backend/alembic/versions/0001_initial_reports_baseline.py backend/alembic/versions/__init__.py backend/tests/test_alembic_migrations.py
  git commit -m "feat(db): introduce alembic with reports baseline migration"
  ```

---

### Task 1.3: Auth tables migration 0002 (upgrade + downgrade)

- [ ] **Step 1: Write the failing test**

  Append to `backend/tests/test_alembic_migrations.py`:

  ```python
  def test_alembic_upgrade_head_fresh_db(alembic_cfg):
      cfg, url = alembic_cfg
      command.upgrade(cfg, "head")
      insp = inspect(create_engine(url))
      tables = set(insp.get_table_names())
      assert {"reports", "users", "user_sessions", "email_tokens", "audit_log"} <= tables
      user_indexes = {ix["name"] for ix in insp.get_indexes("users")}
      sess_indexes = {ix["name"] for ix in insp.get_indexes("user_sessions")}
      assert any("email" in n for n in user_indexes)
      assert any("refresh_token_hash" in n for n in sess_indexes)


  def test_alembic_downgrade_0002(alembic_cfg):
      cfg, url = alembic_cfg
      command.upgrade(cfg, "head")
      command.downgrade(cfg, "0001")
      insp = inspect(create_engine(url))
      tables = set(insp.get_table_names())
      assert "users" not in tables
      assert "user_sessions" not in tables
      assert "email_tokens" not in tables
      assert "audit_log" not in tables
      assert "reports" in tables
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd backend && python -m pytest tests/test_alembic_migrations.py::test_alembic_upgrade_head_fresh_db tests/test_alembic_migrations.py::test_alembic_downgrade_0002 -v`
  Expected: FAIL — `head` resolves only to `0001`; auth tables missing.

- [ ] **Step 3: Implement**

  File: `backend/alembic/versions/0002_auth_tables.py`

  ```python
  """auth tables: users, user_sessions, email_tokens, audit_log

  Revision ID: 0002
  Revises: 0001
  Create Date: 2026-04-13
  """
  from __future__ import annotations

  import sqlalchemy as sa
  from alembic import op

  revision = "0002"
  down_revision = "0001"
  branch_labels = None
  depends_on = None


  def upgrade() -> None:
      op.create_table(
          "users",
          sa.Column("id", sa.String(length=36), primary_key=True),
          sa.Column("email", sa.String(), nullable=False),
          sa.Column("password_hash", sa.String(), nullable=False),
          sa.Column("role", sa.String(), nullable=False, server_default="user"),
          sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
          sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
          sa.Column("totp_secret", sa.String(), nullable=True),
          sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
          sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
          sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
          sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
          sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
      )
      op.create_index("ix_users_email", "users", ["email"], unique=True)

      op.create_table(
          "user_sessions",
          sa.Column("id", sa.String(length=36), primary_key=True),
          sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
          sa.Column("refresh_token_hash", sa.String(), nullable=False),
          sa.Column("user_agent", sa.String(), nullable=True),
          sa.Column("ip_address", sa.String(), nullable=True),
          sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
          sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
          sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
          sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
      )
      op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
      op.create_index("ix_user_sessions_refresh_token_hash", "user_sessions", ["refresh_token_hash"])

      op.create_table(
          "email_tokens",
          sa.Column("id", sa.String(length=36), primary_key=True),
          sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
          sa.Column("token_hash", sa.String(), nullable=False),
          sa.Column("purpose", sa.String(), nullable=False),
          sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
          sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
      )
      op.create_index("ix_email_tokens_user_id", "email_tokens", ["user_id"])
      op.create_index("ix_email_tokens_token_hash", "email_tokens", ["token_hash"])

      op.create_table(
          "audit_log",
          sa.Column("id", sa.String(length=36), primary_key=True),
          sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
          sa.Column("event", sa.String(), nullable=False),
          sa.Column("ip_address", sa.String(), nullable=True),
          sa.Column("user_agent", sa.String(), nullable=True),
          sa.Column("metadata_json", sa.JSON(), nullable=False),
          sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
      )
      op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
      op.create_index("ix_audit_log_event", "audit_log", ["event"])
      op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])


  def downgrade() -> None:
      op.drop_index("ix_audit_log_created_at", table_name="audit_log")
      op.drop_index("ix_audit_log_event", table_name="audit_log")
      op.drop_index("ix_audit_log_user_id", table_name="audit_log")
      op.drop_table("audit_log")

      op.drop_index("ix_email_tokens_token_hash", table_name="email_tokens")
      op.drop_index("ix_email_tokens_user_id", table_name="email_tokens")
      op.drop_table("email_tokens")

      op.drop_index("ix_user_sessions_refresh_token_hash", table_name="user_sessions")
      op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
      op.drop_table("user_sessions")

      op.drop_index("ix_users_email", table_name="users")
      op.drop_table("users")
  ```

  Modify `backend/database.py` — append after existing model imports:

  ```python
  from models import auth as _auth_models  # noqa: F401  keep models registered on SQLModel.metadata
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd backend && python -m pytest tests/test_alembic_migrations.py -v`
  Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

  ```bash
  git add backend/alembic/versions/0002_auth_tables.py backend/database.py backend/tests/test_alembic_migrations.py
  git commit -m "feat(auth): add alembic migration 0002 for auth tables"
  ```

---

## Phase 2: Core Services

**Goal:** Build password, token, TOTP, email, audit services as pure injectable units.

**Files:**
- Create: `backend/services/password_service.py`
- Create: `backend/services/token_service.py`
- Create: `backend/services/totp_service.py`
- Create: `backend/services/email_service.py`
- Create: `backend/services/audit_service.py`
- Modify: `backend/dependencies.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/test_password_service.py`
- Test: `backend/tests/test_token_service.py`
- Test: `backend/tests/test_totp_service.py`
- Test: `backend/tests/test_email_service.py`
- Test: `backend/tests/test_audit_service.py`

---

### Task 2.1: PasswordService (argon2id)

- [ ] **Step 1: Write the failing test**

  File: `backend/tests/test_password_service.py`

  ```python
  import pytest

  from services.password_service import PasswordService


  @pytest.fixture
  def svc():
      return PasswordService()


  def test_password_hash_is_argon2id(svc):
      h = svc.hash("correct horse battery staple")
      assert h.startswith("$argon2id$")


  def test_password_verify_roundtrip(svc):
      h = svc.hash("s3cret-passphrase-12")
      assert svc.verify("s3cret-passphrase-12", h) is True
      assert svc.verify("wrong", h) is False


  def test_password_verify_rejects_tampered_hash(svc):
      h = svc.hash("another-long-pass12")
      tampered = h[:-4] + "AAAA"
      assert svc.verify("another-long-pass12", tampered) is False


  def test_password_verify_rejects_non_argon2(svc):
      bcrypt_like = "$2b$12$abcdefghijklmnopqrstuv.abcdefghijklmnopqrstuvwxyz0123"
      assert svc.verify("whatever", bcrypt_like) is False
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd backend && python -m pytest tests/test_password_service.py -v`
  Expected: FAIL with `ModuleNotFoundError: No module named 'services.password_service'`

- [ ] **Step 3: Implement**

  Add `"passlib[argon2]>=1.7.4"` to `backend/pyproject.toml` dependencies.

  File: `backend/services/password_service.py`

  ```python
  """Argon2id password hashing wrapper around passlib."""
  from __future__ import annotations

  from passlib.context import CryptContext
  from passlib.exc import UnknownHashError


  class PasswordService:
      def __init__(self) -> None:
          self._ctx = CryptContext(
              schemes=["argon2"],
              deprecated="auto",
              argon2__time_cost=3,
              argon2__memory_cost=65536,
              argon2__parallelism=4,
          )

      def hash(self, password: str) -> str:
          return self._ctx.hash(password)

      def verify(self, password: str, password_hash: str) -> bool:
          if not password_hash or not password_hash.startswith("$argon2"):
              return False
          try:
              return self._ctx.verify(password, password_hash)
          except (ValueError, UnknownHashError):
              return False
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd backend && python -m pytest tests/test_password_service.py -v`
  Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

  ```bash
  git add backend/services/password_service.py backend/tests/test_password_service.py backend/pyproject.toml
  git commit -m "feat(auth): add PasswordService with argon2id hashing"
  ```

---

### Task 2.2: TokenService (JWT access + opaque refresh)

- [ ] **Step 1: Write the failing test**

  File: `backend/tests/test_token_service.py`

  ```python
  import time
  from uuid import uuid4

  import jwt
  import pytest

  from services.token_service import TokenService


  @pytest.fixture
  def svc(monkeypatch):
      monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-length!")
      return TokenService()


  def test_jwt_encode_contains_sub_and_exp(svc):
      uid = uuid4()
      tok = svc.encode_access(uid)
      decoded = jwt.decode(tok, "test-secret-32-chars-minimum-length!", algorithms=["HS256"])
      assert decoded["sub"] == str(uid)
      assert decoded["type"] == "access"
      assert "exp" in decoded and "iat" in decoded


  def test_jwt_decode_rejects_bad_signature(svc):
      uid = uuid4()
      tok = svc.encode_access(uid)
      tampered = tok[:-4] + "AAAA"
      with pytest.raises(jwt.InvalidTokenError):
          svc.decode_access(tampered)


  def test_jwt_decode_rejects_expired(svc):
      uid = uuid4()
      payload = {
          "sub": str(uid),
          "type": "access",
          "iat": int(time.time()) - 3600,
          "exp": int(time.time()) - 10,
      }
      expired = jwt.encode(payload, "test-secret-32-chars-minimum-length!", algorithm="HS256")
      with pytest.raises(jwt.ExpiredSignatureError):
          svc.decode_access(expired)


  def test_jwt_decode_rejects_alg_none(svc):
      payload = {"sub": str(uuid4()), "type": "access", "iat": int(time.time()), "exp": int(time.time()) + 60}
      none_token = jwt.encode(payload, key="", algorithm="none")
      with pytest.raises(jwt.InvalidTokenError):
          svc.decode_access(none_token)


  def test_refresh_token_sha256_hash_stable(svc):
      plain, h1 = svc.encode_refresh()
      h2 = svc.hash_refresh(plain)
      assert h1 == h2
      assert len(h1) == 64
      assert plain != h1
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd backend && python -m pytest tests/test_token_service.py -v`
  Expected: FAIL with `ModuleNotFoundError: No module named 'services.token_service'`

- [ ] **Step 3: Implement**

  Add `"pyjwt>=2.9"` to `backend/pyproject.toml` dependencies.

  File: `backend/services/token_service.py`

  ```python
  """JWT access tokens and opaque refresh tokens."""
  from __future__ import annotations

  import hashlib
  import os
  import secrets
  from datetime import datetime, timedelta, timezone
  from uuid import UUID

  import jwt


  class TokenService:
      def __init__(self) -> None:
          secret = os.getenv("JWT_SECRET")
          if not secret:
              raise RuntimeError("JWT_SECRET env var is required")
          self._secret = secret
          self._alg = "HS256"
          self._access_ttl = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_TTL_MINUTES", "15")))

      def encode_access(self, user_id: UUID) -> str:
          now = datetime.now(timezone.utc)
          payload = {
              "sub": str(user_id),
              "type": "access",
              "iat": int(now.timestamp()),
              "exp": int((now + self._access_ttl).timestamp()),
          }
          return jwt.encode(payload, self._secret, algorithm=self._alg)

      def decode_access(self, token: str) -> dict:
          return jwt.decode(
              token,
              self._secret,
              algorithms=[self._alg],
              options={"require": ["exp", "iat", "sub"]},
          )

      def encode_refresh(self) -> tuple[str, str]:
          plain = secrets.token_urlsafe(32)
          return plain, self.hash_refresh(plain)

      def hash_refresh(self, plaintext: str) -> str:
          return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd backend && python -m pytest tests/test_token_service.py -v`
  Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

  ```bash
  git add backend/services/token_service.py backend/tests/test_token_service.py backend/pyproject.toml
  git commit -m "feat(auth): add TokenService for JWT access and opaque refresh tokens"
  ```

---

### Task 2.3: TOTPService (pyotp + Fernet)

- [ ] **Step 1: Write the failing test**

  File: `backend/tests/test_totp_service.py`

  ```python
  import time

  import pyotp
  import pytest
  from cryptography.fernet import Fernet

  from services.totp_service import TOTPService


  @pytest.fixture
  def svc(monkeypatch):
      monkeypatch.setenv("SESSION_ENCRYPTION_KEY", Fernet.generate_key().decode())
      return TOTPService()


  def test_totp_verify_valid_code(svc):
      secret = svc.generate_secret()
      code = pyotp.TOTP(secret).now()
      assert svc.verify(secret, code) is True


  def test_totp_verify_wrong_code(svc):
      secret = svc.generate_secret()
      assert svc.verify(secret, "000000") is False


  def test_totp_verify_drift_window_pm30s(svc):
      secret = svc.generate_secret()
      totp = pyotp.TOTP(secret)
      past_code = totp.at(int(time.time()) - 30)
      assert svc.verify(secret, past_code, valid_window=1) is True


  def test_totp_secret_fernet_encrypted_at_rest(svc):
      secret = svc.generate_secret()
      cipher = svc.encrypt(secret)
      assert cipher != secret
      assert svc.decrypt(cipher) == secret


  def test_totp_provisioning_uri_contains_email(svc):
      secret = svc.generate_secret()
      uri = svc.provisioning_uri(secret, "user@example.com")
      assert uri.startswith("otpauth://totp/")
      assert "user@example.com" in uri
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd backend && python -m pytest tests/test_totp_service.py -v`
  Expected: FAIL with `ModuleNotFoundError: No module named 'services.totp_service'`

- [ ] **Step 3: Implement**

  Add `"pyotp>=2.9"` to `backend/pyproject.toml` dependencies.

  File: `backend/services/totp_service.py`

  ```python
  """TOTP 2FA wrapper with Fernet encryption for secret storage."""
  from __future__ import annotations

  import os

  import pyotp
  from cryptography.fernet import Fernet


  class TOTPService:
      _ISSUER = "Logopaedie Report Agent"

      def __init__(self) -> None:
          key = os.getenv("SESSION_ENCRYPTION_KEY")
          if not key:
              raise RuntimeError("SESSION_ENCRYPTION_KEY env var is required")
          self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

      def generate_secret(self) -> str:
          return pyotp.random_base32()

      def provisioning_uri(self, secret: str, email: str) -> str:
          return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=self._ISSUER)

      def verify(self, secret: str, code: str, valid_window: int = 1) -> bool:
          if not code or not code.isdigit() or len(code) != 6:
              return False
          return pyotp.TOTP(secret).verify(code, valid_window=valid_window)

      def encrypt(self, secret: str) -> str:
          return self._fernet.encrypt(secret.encode("utf-8")).decode("utf-8")

      def decrypt(self, cipher: str) -> str:
          return self._fernet.decrypt(cipher.encode("utf-8")).decode("utf-8")
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd backend && python -m pytest tests/test_totp_service.py -v`
  Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

  ```bash
  git add backend/services/totp_service.py backend/tests/test_totp_service.py backend/pyproject.toml
  git commit -m "feat(auth): add TOTPService with Fernet-encrypted secret storage"
  ```

---

### Task 2.4: EmailService (Resend + console fallback)

- [ ] **Step 1: Write the failing test**

  File: `backend/tests/test_email_service.py`

  ```python
  import pytest

  from services.email_service import EmailService, FakeEmailService


  def test_email_service_console_fallback_when_no_api_key(capsys, monkeypatch):
      monkeypatch.delenv("RESEND_API_KEY", raising=False)
      monkeypatch.setenv("APP_URL", "http://localhost:3000")
      monkeypatch.setenv("EMAIL_FROM", "noreply@test.local")
      svc = EmailService()
      svc.send_verify_email("alice@example.com", "tok123")
      out = capsys.readouterr().out
      assert "EMAIL (console mode)" in out
      assert "alice@example.com" in out
      assert "tok123" in out


  def test_email_service_reset_template_contains_reset_link(capsys, monkeypatch):
      monkeypatch.delenv("RESEND_API_KEY", raising=False)
      monkeypatch.setenv("APP_URL", "http://localhost:3000")
      monkeypatch.setenv("EMAIL_FROM", "noreply@test.local")
      svc = EmailService()
      svc.send_password_reset("bob@example.com", "resettok")
      out = capsys.readouterr().out
      assert "reset-password?token=resettok" in out


  def test_fake_email_service_records_calls():
      fake = FakeEmailService()
      fake.send_verify_email("x@example.com", "t1")
      fake.send_password_reset("y@example.com", "t2")
      assert len(fake.sent) == 2
      assert fake.sent[0] == ("verify", "x@example.com", "t1")
      assert fake.sent[1] == ("reset", "y@example.com", "t2")
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd backend && python -m pytest tests/test_email_service.py -v`
  Expected: FAIL with `ModuleNotFoundError: No module named 'services.email_service'`

- [ ] **Step 3: Implement**

  Add `"resend>=0.8"` and `"user-agents>=2.2"` to `backend/pyproject.toml` dependencies.

  File: `backend/services/email_service.py`

  ```python
  """Email delivery via Resend SDK, with console fallback for local dev."""
  from __future__ import annotations

  import os
  from typing import Literal


  class EmailService:
      def __init__(self) -> None:
          self._api_key = os.getenv("RESEND_API_KEY", "")
          self._from = os.getenv("EMAIL_FROM", "noreply@localhost")
          self._app_url = os.getenv("APP_URL", "http://localhost:3000")

      def _send(self, to: str, subject: str, body: str) -> None:
          if not self._api_key:
              print(f"EMAIL (console mode) -> {to}\nSubject: {subject}\n{body}\n")
              return
          import resend  # type: ignore

          resend.api_key = self._api_key
          resend.Emails.send({"from": self._from, "to": [to], "subject": subject, "text": body})

      def send_verify_email(self, to: str, token: str) -> None:
          link = f"{self._app_url}/verify-email?token={token}"
          body = (
              f"Welcome. Please verify your email by clicking:\n{link}\n"
              "If you did not create an account, ignore this message."
          )
          self._send(to, "Verify your email", body)

      def send_password_reset(self, to: str, token: str) -> None:
          link = f"{self._app_url}/reset-password?token={token}"
          body = (
              f"A password reset was requested. Click to continue:\n{link}\n"
              "If you did not request this, you can safely ignore this message."
          )
          self._send(to, "Password reset request", body)


  class FakeEmailService:
      def __init__(self) -> None:
          self.sent: list[tuple[Literal["verify", "reset"], str, str]] = []

      def send_verify_email(self, to: str, token: str) -> None:
          self.sent.append(("verify", to, token))

      def send_password_reset(self, to: str, token: str) -> None:
          self.sent.append(("reset", to, token))
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd backend && python -m pytest tests/test_email_service.py -v`
  Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

  ```bash
  git add backend/services/email_service.py backend/tests/test_email_service.py backend/pyproject.toml
  git commit -m "feat(auth): add EmailService with Resend backend and console fallback"
  ```

---

### Task 2.5: AuditService (synchronous, fail-closed)

- [ ] **Step 1: Write the failing test**

  File: `backend/tests/test_audit_service.py`

  ```python
  import pytest
  from sqlmodel import Session, SQLModel, create_engine, select

  from models.auth import AuditLog, User
  from services.audit_service import AuditService


  @pytest.fixture
  def db():
      eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
      SQLModel.metadata.create_all(eng)
      with Session(eng) as session:
          yield session


  def test_audit_log_insert_writes_row(db):
      user = User(email="a@example.com", password_hash="x")
      db.add(user)
      db.commit()
      db.refresh(user)
      AuditService().log(
          db,
          user_id=user.id,
          event="login.success",
          ip="1.2.3.4",
          user_agent="pytest",
          metadata={"ok": True},
      )
      row = db.exec(select(AuditLog)).one()
      assert row.event == "login.success"
      assert row.ip_address == "1.2.3.4"
      assert row.metadata_json == {"ok": True}


  def test_audit_log_user_id_nullable(db):
      AuditService().log(
          db,
          user_id=None,
          event="login.fail",
          ip="1.2.3.4",
          user_agent="pytest",
          metadata={"reason": "bad_password"},
      )
      row = db.exec(select(AuditLog)).one()
      assert row.user_id is None


  def test_audit_log_failure_raises_fail_closed(db):
      class BrokenSession:
          def add(self, *_args, **_kwargs):
              raise RuntimeError("db down")

          def commit(self):
              raise RuntimeError("db down")

      with pytest.raises(RuntimeError, match="db down"):
          AuditService().log(
              BrokenSession(),  # type: ignore[arg-type]
              user_id=None,
              event="test.event",
              ip=None,
              user_agent=None,
              metadata={},
          )
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd backend && python -m pytest tests/test_audit_service.py -v`
  Expected: FAIL with `ModuleNotFoundError: No module named 'services.audit_service'`

- [ ] **Step 3: Implement**

  File: `backend/services/audit_service.py`

  ```python
  """Synchronous, fail-closed audit logger."""
  from __future__ import annotations

  from uuid import UUID

  from sqlmodel import Session

  from models.auth import AuditLog


  class AuditService:
      def log(
          self,
          db: Session,
          *,
          user_id: UUID | None,
          event: str,
          ip: str | None,
          user_agent: str | None,
          metadata: dict,
      ) -> None:
          entry = AuditLog(
              user_id=user_id,
              event=event,
              ip_address=ip,
              user_agent=user_agent,
              metadata_json=metadata,
          )
          db.add(entry)
          db.commit()
  ```

  Modify `backend/dependencies.py` — add singletons:

  ```python
  from functools import lru_cache

  from services.audit_service import AuditService
  from services.email_service import EmailService
  from services.password_service import PasswordService
  from services.token_service import TokenService
  from services.totp_service import TOTPService


  @lru_cache(maxsize=1)
  def get_password_service() -> PasswordService:
      return PasswordService()


  @lru_cache(maxsize=1)
  def get_token_service() -> TokenService:
      return TokenService()


  @lru_cache(maxsize=1)
  def get_totp_service() -> TOTPService:
      return TOTPService()


  @lru_cache(maxsize=1)
  def get_email_service() -> EmailService:
      return EmailService()


  @lru_cache(maxsize=1)
  def get_audit_service() -> AuditService:
      return AuditService()
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd backend && python -m pytest tests/test_audit_service.py -v`
  Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

  ```bash
  git add backend/services/audit_service.py backend/tests/test_audit_service.py backend/dependencies.py
  git commit -m "feat(auth): add AuditService and wire service singletons"
  ```

---

### Task 2.6: Opus Gate 2A — Security review (token + password services)

**Security Review (Opus subagent)**

Run this Opus security review before moving to Phase 3. The human operator copy-pastes the invocation below into a fresh Claude Code session:

````
Agent({
  subagent_type: "general-purpose",
  model: "opus",
  description: "Opus security review: token + password services",
  prompt: "Review backend/services/token_service.py and backend/services/password_service.py for the following threats and anti-patterns. Produce a structured report with severity (critical/high/medium/low), file:line, and proposed patch for each finding.\n\n1. JWT algorithm pinning: confirm decode_access pins algorithms=['HS256'] and rejects alg=none and HS/RS confusion. Walk through what happens if an attacker submits a token with alg='none' or alg='RS256' against an HS256 secret.\n2. Claims validation: confirm exp/iat are required, check clock-skew behavior (leeway), confirm 'sub' is validated as a non-empty string mapping to a UUID.\n3. Refresh token entropy: confirm secrets.token_urlsafe(32) yields >=192 bits of entropy and that hash_refresh uses sha256 hex (64 chars) deterministically.\n4. passlib configuration: confirm schemes=['argon2'] locks the scheme with no silent bcrypt fallback, and that verify() returns False for any non-argon2 input rather than raising. Confirm argon2 params time_cost=3 memory_cost=65536 parallelism=4 are acceptable for a Vercel-hosted FastAPI workload (not too slow under concurrent login).\n5. Constant-time verification: confirm passlib's internal constant-time compare path is used and that the non-argon2 early-return does NOT introduce a timing oracle distinguishing 'user exists with bcrypt hash' from 'user does not exist'. Suggest using a dummy argon2 hash as the sentinel in auth_service instead.\n6. Secret handling: confirm JWT_SECRET is read from env and never logged; flag any path that could leak it in exception messages.\n\nFor each finding: (a) quote the exact lines, (b) describe the attack scenario, (c) provide a concrete patch as a unified diff. If all checks pass, say so explicitly with a one-line confirmation per item."
})
````

- [ ] **Step 1: Invoke Opus gate (copy the block above).**
- [ ] **Step 2: Apply any patches Opus recommends as follow-up commits, one per finding.**
- [ ] **Step 3: Re-run phase 2 test suite.**
  Run: `cd backend && python -m pytest tests/test_password_service.py tests/test_token_service.py -v`
  Expected: PASS
- [ ] **Step 4: Commit any fixes with message** `fix(auth): address opus gate 2A findings`.

---

## Phase 3: Auth Routes (no 2FA)

**Goal:** Implement register/verify/login/logout/refresh/me/password-reset endpoints, JWT middleware, service-token middleware, and the exception hierarchy.

**Files:**
- Create: `backend/routers/auth.py`
- Create: `backend/middleware/service_token.py`
- Create: `backend/services/auth_service.py`
- Modify: `backend/middleware/auth.py` (REPLACE contents)
- Modify: `backend/exceptions.py`
- Modify: `backend/dependencies.py`
- Modify: `backend/main.py`
- Test: `backend/tests/test_auth_routes.py`
- Test: `backend/tests/test_auth_middleware.py`
- Test: `backend/tests/test_auth_service.py`
- Test: `backend/tests/test_security_enumeration.py`
- Test: `backend/tests/test_service_token_middleware.py`

---

### Task 3.1: Exception hierarchy, JWT middleware, and ServiceToken middleware

- [ ] **Step 1: Write the failing test**

  File: `backend/tests/test_auth_middleware.py`

  ```python
  from uuid import uuid4

  import pytest
  from fastapi import FastAPI
  from fastapi.testclient import TestClient
  from starlette.requests import Request

  from middleware.auth import JWTAuthMiddleware
  from services.token_service import TokenService


  @pytest.fixture
  def app(monkeypatch):
      monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-length!")
      application = FastAPI()
      application.add_middleware(JWTAuthMiddleware)

      @application.get("/whoami")
      def whoami(request: Request):
          return {"user": request.state.user}

      return application


  def test_middleware_no_header_sets_user_none(app):
      client = TestClient(app)
      res = client.get("/whoami")
      assert res.status_code == 200
      assert res.json() == {"user": None}


  def test_middleware_valid_token_populates_user(app, monkeypatch):
      monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-length!")
      svc = TokenService()
      uid = uuid4()
      tok = svc.encode_access(uid)
      client = TestClient(app)
      res = client.get("/whoami", headers={"Authorization": f"Bearer {tok}"})
      assert res.status_code == 200
      assert res.json()["user"]["id"] == str(uid)


  def test_middleware_invalid_token_sets_user_none_never_401(app):
      client = TestClient(app)
      res = client.get("/whoami", headers={"Authorization": "Bearer not-a-jwt"})
      assert res.status_code == 200
      assert res.json() == {"user": None}
  ```

  File: `backend/tests/test_service_token_middleware.py`

  ```python
  import pytest
  from fastapi import FastAPI
  from fastapi.testclient import TestClient

  from middleware.service_token import ServiceTokenMiddleware


  @pytest.fixture
  def app(monkeypatch):
      monkeypatch.setenv("SERVICE_TOKEN", "svc-secret")
      application = FastAPI()
      application.add_middleware(ServiceTokenMiddleware)

      @application.get("/health")
      def health():
          return {"ok": True}

      @application.get("/cron/cleanup")
      def cleanup():
          return {"ran": True}

      @application.get("/other")
      def other():
          return {"other": True}

      return application


  def test_service_token_middleware_health_requires_token(app):
      client = TestClient(app)
      assert client.get("/health").status_code == 401
      ok = client.get("/health", headers={"Authorization": "Bearer svc-secret"})
      assert ok.status_code == 200


  def test_service_token_middleware_cron_requires_token(app):
      client = TestClient(app)
      assert client.get("/cron/cleanup").status_code == 401
      ok = client.get("/cron/cleanup", headers={"Authorization": "Bearer svc-secret"})
      assert ok.status_code == 200


  def test_service_token_middleware_other_paths_passthrough(app):
      client = TestClient(app)
      res = client.get("/other")
      assert res.status_code == 200


  def test_service_token_middleware_inactive_when_env_unset(monkeypatch):
      monkeypatch.delenv("SERVICE_TOKEN", raising=False)
      app = FastAPI()
      app.add_middleware(ServiceTokenMiddleware)

      @app.get("/health")
      def health():
          return {"ok": True}

      assert TestClient(app).get("/health").status_code == 200
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd backend && python -m pytest tests/test_auth_middleware.py tests/test_service_token_middleware.py -v`
  Expected: FAIL — `middleware.auth.JWTAuthMiddleware` and `middleware.service_token.ServiceTokenMiddleware` do not exist yet.

- [ ] **Step 3: Implement**

  REPLACE `backend/middleware/auth.py`:

  ```python
  """JWT auth middleware — non-throwing, populates request.state.user."""
  from __future__ import annotations

  import os

  import jwt
  from starlette.middleware.base import BaseHTTPMiddleware
  from starlette.requests import Request
  from starlette.responses import Response


  class JWTAuthMiddleware(BaseHTTPMiddleware):
      SKIP_PREFIXES = ("/health", "/cron/")

      async def dispatch(self, request: Request, call_next) -> Response:
          request.state.user = None
          if request.method == "OPTIONS" or request.url.path.startswith(self.SKIP_PREFIXES):
              return await call_next(request)

          auth = request.headers.get("authorization", "")
          if not auth.lower().startswith("bearer "):
              return await call_next(request)
          token = auth.split(" ", 1)[1].strip()

          secret = os.getenv("JWT_SECRET")
          if not secret or not token:
              return await call_next(request)
          try:
              payload = jwt.decode(
                  token,
                  secret,
                  algorithms=["HS256"],
                  options={"require": ["exp", "iat", "sub"]},
              )
              if payload.get("type") != "access":
                  return await call_next(request)
              request.state.user = {"id": payload["sub"], "role": payload.get("role", "user")}
          except jwt.InvalidTokenError:
              request.state.user = None
          return await call_next(request)
  ```

  File: `backend/middleware/service_token.py`

  ```python
  """Service-token middleware: guards /health and /cron/* paths."""
  from __future__ import annotations

  import os

  from starlette.middleware.base import BaseHTTPMiddleware
  from starlette.requests import Request
  from starlette.responses import JSONResponse, Response


  class ServiceTokenMiddleware(BaseHTTPMiddleware):
      GUARDED_PREFIXES = ("/health", "/cron/")

      async def dispatch(self, request: Request, call_next) -> Response:
          path = request.url.path
          if not path.startswith(self.GUARDED_PREFIXES):
              return await call_next(request)

          expected = os.getenv("SERVICE_TOKEN")
          if not expected:
              return await call_next(request)

          auth = request.headers.get("authorization", "")
          if auth != f"Bearer {expected}":
              return JSONResponse({"error": "unauthorized"}, status_code=401)
          return await call_next(request)
  ```

  Append to `backend/exceptions.py`:

  ```python
  from fastapi import status


  class AuthError(Exception):
      status_code = status.HTTP_401_UNAUTHORIZED
      error_code = "auth_error"
      message = "Authentication required"


  class InvalidCredentialsError(AuthError):
      error_code = "invalid_credentials"
      message = "Email or password incorrect"


  class EmailNotVerifiedError(AuthError):
      status_code = status.HTTP_403_FORBIDDEN
      error_code = "email_not_verified"
      message = "Email not verified"


  class AccountLockedError(AuthError):
      status_code = status.HTTP_423_LOCKED
      error_code = "account_locked"
      message = "Account temporarily locked"

      def __init__(self, locked_until: str | None = None) -> None:
          super().__init__()
          self.locked_until = locked_until


  class TokenInvalidError(AuthError):
      error_code = "token_invalid"
      message = "Token invalid or expired"
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd backend && python -m pytest tests/test_auth_middleware.py tests/test_service_token_middleware.py -v`
  Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

  ```bash
  git add backend/middleware/auth.py backend/middleware/service_token.py backend/exceptions.py backend/tests/test_auth_middleware.py backend/tests/test_service_token_middleware.py
  git commit -m "feat(auth): add JWT and service-token middleware plus auth exception hierarchy"
  ```

---

### Task 3.2: AuthService — register and verify_email

- [ ] **Step 1: Write the failing test**

  File: `backend/tests/test_auth_service.py`

  ```python
  import hashlib
  from datetime import datetime, timedelta, timezone

  import pytest
  from sqlmodel import Session, SQLModel, create_engine, select

  from models.auth import EmailToken, User, UserSession
  from services.audit_service import AuditService
  from services.auth_service import AuthService
  from services.email_service import FakeEmailService
  from services.password_service import PasswordService
  from services.token_service import TokenService


  @pytest.fixture
  def deps(monkeypatch):
      monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-length!")
      eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
      SQLModel.metadata.create_all(eng)
      email = FakeEmailService()
      svc = AuthService(
          password=PasswordService(),
          tokens=TokenService(),
          email=email,
          audit=AuditService(),
      )
      with Session(eng) as db:
          yield svc, db, email


  def test_register_creates_user_and_sends_verify_email(deps):
      svc, db, email = deps
      svc.register(db, email_addr="alice@example.com", password="longpassword12", ip="1.1.1.1", ua="pytest")
      users = db.exec(select(User)).all()
      assert len(users) == 1
      assert users[0].email == "alice@example.com"
      assert users[0].email_verified is False
      assert len(email.sent) == 1
      assert email.sent[0][0] == "verify"


  def test_register_duplicate_email_no_email_sent(deps):
      svc, db, email = deps
      svc.register(db, email_addr="dup@example.com", password="longpassword12", ip=None, ua=None)
      email.sent.clear()
      svc.register(db, email_addr="dup@example.com", password="otherlongpass12", ip=None, ua=None)
      assert email.sent == []
      assert len(db.exec(select(User)).all()) == 1


  def test_verify_email_valid_token_marks_verified(deps):
      svc, db, email = deps
      svc.register(db, email_addr="v@example.com", password="longpassword12", ip=None, ua=None)
      plain_token = email.sent[-1][2]
      svc.verify_email(db, token=plain_token, ip=None, ua=None)
      user = db.exec(select(User).where(User.email == "v@example.com")).one()
      assert user.email_verified is True
      assert user.email_verified_at is not None


  def test_verify_email_reused_token_rejected(deps):
      svc, db, email = deps
      svc.register(db, email_addr="r@example.com", password="longpassword12", ip=None, ua=None)
      plain_token = email.sent[-1][2]
      svc.verify_email(db, token=plain_token, ip=None, ua=None)
      from exceptions import TokenInvalidError

      with pytest.raises(TokenInvalidError):
          svc.verify_email(db, token=plain_token, ip=None, ua=None)


  def test_verify_email_expired_token_rejected(deps):
      svc, db, email = deps
      svc.register(db, email_addr="e@example.com", password="longpassword12", ip=None, ua=None)
      plain_token = email.sent[-1][2]
      token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
      tok = db.exec(select(EmailToken).where(EmailToken.token_hash == token_hash)).one()
      tok.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
      db.add(tok)
      db.commit()
      from exceptions import TokenInvalidError

      with pytest.raises(TokenInvalidError):
          svc.verify_email(db, token=plain_token, ip=None, ua=None)
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd backend && python -m pytest tests/test_auth_service.py -v`
  Expected: FAIL — `services.auth_service` module does not exist.

- [ ] **Step 3: Implement**

  File: `backend/services/auth_service.py`

  ```python
  """Business logic for register/verify/login/refresh/reset flows (no 2FA)."""
  from __future__ import annotations

  import hashlib
  import secrets
  from datetime import datetime, timedelta, timezone

  from sqlmodel import Session, select

  from exceptions import (
      AccountLockedError,
      EmailNotVerifiedError,
      InvalidCredentialsError,
      TokenInvalidError,
  )
  from models.auth import EmailToken, User, UserSession
  from services.audit_service import AuditService
  from services.email_service import EmailService, FakeEmailService
  from services.password_service import PasswordService
  from services.token_service import TokenService

  _DUMMY_HASH = PasswordService().hash("dummy-timing-equalizer-unguessable-12345")


  def _utcnow() -> datetime:
      return datetime.now(timezone.utc)


  def _sha256(s: str) -> str:
      return hashlib.sha256(s.encode("utf-8")).hexdigest()


  class AuthService:
      LOCKOUT_THRESHOLD = 10
      LOCKOUT_DURATION = timedelta(minutes=15)
      REFRESH_TTL = timedelta(days=7)
      RESET_TTL = timedelta(hours=1)

      def __init__(
          self,
          *,
          password: PasswordService,
          tokens: TokenService,
          email: EmailService | FakeEmailService,
          audit: AuditService,
      ) -> None:
          self.password = password
          self.tokens = tokens
          self.email = email
          self.audit = audit

      def _user_view(self, user: User) -> dict:
          return {
              "id": str(user.id),
              "email": user.email,
              "role": user.role,
              "totp_enabled": user.totp_enabled,
              "created_at": user.created_at.isoformat(),
          }

      # ---------- register + verify ----------

      def register(self, db: Session, *, email_addr: str, password: str, ip: str | None, ua: str | None) -> None:
          normalized = email_addr.strip().lower()
          if len(password) < 12:
              raise ValueError("password_too_short")
          existing = db.exec(select(User).where(User.email == normalized)).first()
          self.audit.log(
              db,
              user_id=existing.id if existing else None,
              event="user.register_attempt",
              ip=ip,
              user_agent=ua,
              metadata={"email": normalized},
          )
          if existing is not None:
              return
          user = User(email=normalized, password_hash=self.password.hash(password))
          db.add(user)
          db.commit()
          db.refresh(user)
          plain = secrets.token_urlsafe(32)
          db.add(
              EmailToken(
                  user_id=user.id,
                  token_hash=_sha256(plain),
                  purpose="verify_email",
                  expires_at=_utcnow() + timedelta(hours=24),
              )
          )
          db.commit()
          self.email.send_verify_email(normalized, plain)

      def verify_email(self, db: Session, *, token: str, ip: str | None, ua: str | None) -> None:
          token_hash = _sha256(token)
          row = db.exec(
              select(EmailToken).where(
                  EmailToken.token_hash == token_hash,
                  EmailToken.purpose == "verify_email",
              )
          ).first()
          if row is None or row.used_at is not None or row.expires_at < _utcnow():
              raise TokenInvalidError()
          row.used_at = _utcnow()
          user = db.exec(select(User).where(User.id == row.user_id)).one()
          user.email_verified = True
          user.email_verified_at = _utcnow()
          user.updated_at = _utcnow()
          db.add(row)
          db.add(user)
          db.commit()
          self.audit.log(db, user_id=user.id, event="user.email_verified", ip=ip, user_agent=ua, metadata={})
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd backend && python -m pytest tests/test_auth_service.py -v`
  Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

  ```bash
  git add backend/services/auth_service.py backend/tests/test_auth_service.py
  git commit -m "feat(auth): add AuthService with register and email verification flows"
  ```

---

### Task 3.3: AuthService — login, lockout, refresh rotation, reuse detection, logout

- [ ] **Step 1: Write the failing test**

  Append to `backend/tests/test_auth_service.py`:

  ```python
  def _make_verified_user(svc: AuthService, db, email_svc, email: str, password: str = "longpassword12"):
      svc.register(db, email_addr=email, password=password, ip=None, ua=None)
      plain_token = email_svc.sent[-1][2]
      svc.verify_email(db, token=plain_token, ip=None, ua=None)


  def test_login_unverified_raises_email_not_verified(deps):
      svc, db, email = deps
      svc.register(db, email_addr="u@example.com", password="longpassword12", ip=None, ua=None)
      from exceptions import EmailNotVerifiedError
      with pytest.raises(EmailNotVerifiedError):
          svc.login(db, email_addr="u@example.com", password="longpassword12", ip=None, ua=None)


  def test_login_wrong_password_generic(deps):
      svc, db, email = deps
      _make_verified_user(svc, db, email, "good@example.com")
      from exceptions import InvalidCredentialsError
      with pytest.raises(InvalidCredentialsError):
          svc.login(db, email_addr="good@example.com", password="wrongpassword12", ip=None, ua=None)


  def test_login_unknown_email_generic(deps):
      svc, db, email = deps
      from exceptions import InvalidCredentialsError
      with pytest.raises(InvalidCredentialsError):
          svc.login(db, email_addr="nobody@example.com", password="longpassword12", ip=None, ua=None)


  def test_login_success_returns_tokens(deps):
      svc, db, email = deps
      _make_verified_user(svc, db, email, "ok@example.com")
      result = svc.login(db, email_addr="ok@example.com", password="longpassword12", ip="1.1.1.1", ua="pytest")
      assert "access_token" in result and "refresh_token" in result
      assert result["user"]["email"] == "ok@example.com"
      sessions = db.exec(select(UserSession)).all()
      assert len(sessions) == 1


  def test_login_lockout_after_10_fails(deps):
      svc, db, email = deps
      _make_verified_user(svc, db, email, "lock@example.com")
      from exceptions import AccountLockedError, InvalidCredentialsError
      for _ in range(10):
          with pytest.raises(InvalidCredentialsError):
              svc.login(db, email_addr="lock@example.com", password="wrongpassword12", ip=None, ua=None)
      with pytest.raises(AccountLockedError):
          svc.login(db, email_addr="lock@example.com", password="longpassword12", ip=None, ua=None)


  def test_refresh_rotates_token(deps):
      svc, db, email = deps
      _make_verified_user(svc, db, email, "rot@example.com")
      first = svc.login(db, email_addr="rot@example.com", password="longpassword12", ip=None, ua=None)
      second = svc.refresh(db, refresh_token=first["refresh_token"], ip=None, ua=None)
      assert second["refresh_token"] != first["refresh_token"]
      from exceptions import TokenInvalidError
      with pytest.raises(TokenInvalidError):
          svc.refresh(db, refresh_token=first["refresh_token"], ip=None, ua=None)


  def test_refresh_reuse_revokes_all_sessions(deps):
      svc, db, email = deps
      _make_verified_user(svc, db, email, "reuse@example.com")
      first = svc.login(db, email_addr="reuse@example.com", password="longpassword12", ip=None, ua=None)
      _ = svc.login(db, email_addr="reuse@example.com", password="longpassword12", ip=None, ua=None)
      svc.refresh(db, refresh_token=first["refresh_token"], ip=None, ua=None)
      from exceptions import TokenInvalidError
      with pytest.raises(TokenInvalidError):
          svc.refresh(db, refresh_token=first["refresh_token"], ip=None, ua=None)
      active = db.exec(select(UserSession).where(UserSession.revoked_at.is_(None))).all()
      assert active == []
      from models.auth import AuditLog
      events = [row.event for row in db.exec(select(AuditLog)).all()]
      assert "session.refresh_reuse_detected" in events
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd backend && python -m pytest tests/test_auth_service.py -v`
  Expected: FAIL — `AuthService.login` / `.refresh` / `.logout` not yet implemented.

- [ ] **Step 3: Implement**

  Append to the `AuthService` class in `backend/services/auth_service.py`:

  ```python
      # ---------- login ----------

      def login(self, db: Session, *, email_addr: str, password: str, ip: str | None, ua: str | None) -> dict:
          normalized = email_addr.strip().lower()
          user = db.exec(select(User).where(User.email == normalized)).first()

          if user is None:
              # Equalize timing against dummy argon2 hash.
              self.password.verify(password, _DUMMY_HASH)
              self.audit.log(db, user_id=None, event="login.fail", ip=ip, user_agent=ua,
                             metadata={"reason": "unknown_email"})
              raise InvalidCredentialsError()

          if user.locked_until is not None and user.locked_until > _utcnow():
              self.audit.log(db, user_id=user.id, event="login.fail", ip=ip, user_agent=ua,
                             metadata={"reason": "locked"})
              raise AccountLockedError(locked_until=user.locked_until.isoformat())

          if not self.password.verify(password, user.password_hash):
              user.failed_login_count += 1
              if user.failed_login_count >= self.LOCKOUT_THRESHOLD:
                  user.locked_until = _utcnow() + self.LOCKOUT_DURATION
              user.updated_at = _utcnow()
              db.add(user)
              db.commit()
              self.audit.log(db, user_id=user.id, event="login.fail", ip=ip, user_agent=ua,
                             metadata={"reason": "bad_password", "attempts": user.failed_login_count})
              raise InvalidCredentialsError()

          if not user.email_verified:
              self.audit.log(db, user_id=user.id, event="login.fail", ip=ip, user_agent=ua,
                             metadata={"reason": "not_verified"})
              raise EmailNotVerifiedError()

          user.failed_login_count = 0
          user.locked_until = None
          user.updated_at = _utcnow()
          db.add(user)

          plain_refresh, refresh_hash = self.tokens.encode_refresh()
          sess = UserSession(
              user_id=user.id,
              refresh_token_hash=refresh_hash,
              user_agent=ua,
              ip_address=ip,
              expires_at=_utcnow() + self.REFRESH_TTL,
          )
          db.add(sess)
          db.commit()
          self.audit.log(db, user_id=user.id, event="login.success", ip=ip, user_agent=ua, metadata={})
          return {
              "access_token": self.tokens.encode_access(user.id),
              "refresh_token": plain_refresh,
              "user": self._user_view(user),
          }

      # ---------- refresh rotation + reuse detection ----------

      def refresh(self, db: Session, *, refresh_token: str, ip: str | None, ua: str | None) -> dict:
          token_hash = self.tokens.hash_refresh(refresh_token)
          row = db.exec(select(UserSession).where(UserSession.refresh_token_hash == token_hash)).first()
          if row is None:
              raise TokenInvalidError()
          if row.revoked_at is not None:
              for s in db.exec(select(UserSession).where(UserSession.user_id == row.user_id)).all():
                  if s.revoked_at is None:
                      s.revoked_at = _utcnow()
                      db.add(s)
              db.commit()
              self.audit.log(db, user_id=row.user_id, event="session.refresh_reuse_detected",
                             ip=ip, user_agent=ua, metadata={"session_id": str(row.id)})
              raise TokenInvalidError()
          if row.expires_at < _utcnow():
              raise TokenInvalidError()

          row.revoked_at = _utcnow()
          db.add(row)
          new_plain, new_hash = self.tokens.encode_refresh()
          new_row = UserSession(
              user_id=row.user_id,
              refresh_token_hash=new_hash,
              user_agent=ua,
              ip_address=ip,
              expires_at=_utcnow() + self.REFRESH_TTL,
          )
          db.add(new_row)
          db.commit()
          user = db.exec(select(User).where(User.id == row.user_id)).one()
          return {
              "access_token": self.tokens.encode_access(user.id),
              "refresh_token": new_plain,
              "user": self._user_view(user),
          }

      # ---------- logout ----------

      def logout(self, db: Session, *, refresh_token: str, ip: str | None, ua: str | None) -> None:
          token_hash = self.tokens.hash_refresh(refresh_token)
          row = db.exec(select(UserSession).where(UserSession.refresh_token_hash == token_hash)).first()
          if row is not None and row.revoked_at is None:
              row.revoked_at = _utcnow()
              db.add(row)
              db.commit()
              self.audit.log(db, user_id=row.user_id, event="logout", ip=ip, user_agent=ua,
                             metadata={"session_id": str(row.id)})
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd backend && python -m pytest tests/test_auth_service.py -v`
  Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

  ```bash
  git add backend/services/auth_service.py backend/tests/test_auth_service.py
  git commit -m "feat(auth): add login with lockout, refresh rotation with reuse detection, logout"
  ```

---

### Task 3.4: AuthService — password reset, change, resend-verification

- [ ] **Step 1: Write the failing test**

  Append to `backend/tests/test_auth_service.py`:

  ```python
  def test_password_reset_request_unknown_email_silent(deps):
      svc, db, email = deps
      svc.request_password_reset(db, email_addr="ghost@example.com", ip=None, ua=None)
      assert email.sent == []


  def test_password_reset_confirm_revokes_all_sessions(deps):
      svc, db, email = deps
      _make_verified_user(svc, db, email, "reset@example.com")
      svc.login(db, email_addr="reset@example.com", password="longpassword12", ip=None, ua=None)
      svc.login(db, email_addr="reset@example.com", password="longpassword12", ip=None, ua=None)
      email.sent.clear()
      svc.request_password_reset(db, email_addr="reset@example.com", ip=None, ua=None)
      reset_token = email.sent[-1][2]
      svc.confirm_password_reset(db, token=reset_token, new_password="newlongpassword34", ip=None, ua=None)
      active = db.exec(select(UserSession).where(UserSession.revoked_at.is_(None))).all()
      assert active == []
      svc.login(db, email_addr="reset@example.com", password="newlongpassword34", ip=None, ua=None)


  def test_password_change_revokes_other_sessions_only(deps):
      svc, db, email = deps
      _make_verified_user(svc, db, email, "ch@example.com")
      s1 = svc.login(db, email_addr="ch@example.com", password="longpassword12", ip=None, ua=None)
      _s2 = svc.login(db, email_addr="ch@example.com", password="longpassword12", ip=None, ua=None)
      user = db.exec(select(User).where(User.email == "ch@example.com")).one()
      svc.change_password(
          db,
          user=user,
          current_password="longpassword12",
          new_password="newlongpassword34",
          current_refresh_token=s1["refresh_token"],
          ip=None,
          ua=None,
      )
      active = db.exec(select(UserSession).where(UserSession.revoked_at.is_(None))).all()
      assert len(active) == 1
      svc.refresh(db, refresh_token=s1["refresh_token"], ip=None, ua=None)
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd backend && python -m pytest tests/test_auth_service.py -v`
  Expected: FAIL — `request_password_reset` / `confirm_password_reset` / `change_password` not yet implemented.

- [ ] **Step 3: Implement**

  Append to the `AuthService` class in `backend/services/auth_service.py`:

  ```python
      # ---------- password reset ----------

      def request_password_reset(self, db: Session, *, email_addr: str, ip: str | None, ua: str | None) -> None:
          normalized = email_addr.strip().lower()
          user = db.exec(select(User).where(User.email == normalized)).first()
          self.audit.log(db, user_id=user.id if user else None, event="password.reset_requested",
                         ip=ip, user_agent=ua, metadata={"email": normalized})
          if user is None:
              return
          plain = secrets.token_urlsafe(32)
          db.add(
              EmailToken(
                  user_id=user.id,
                  token_hash=_sha256(plain),
                  purpose="reset_password",
                  expires_at=_utcnow() + self.RESET_TTL,
              )
          )
          db.commit()
          self.email.send_password_reset(normalized, plain)

      def confirm_password_reset(self, db: Session, *, token: str, new_password: str,
                                 ip: str | None, ua: str | None) -> None:
          if len(new_password) < 12:
              raise TokenInvalidError()
          token_hash = _sha256(token)
          row = db.exec(
              select(EmailToken).where(
                  EmailToken.token_hash == token_hash,
                  EmailToken.purpose == "reset_password",
              )
          ).first()
          if row is None or row.used_at is not None or row.expires_at < _utcnow():
              raise TokenInvalidError()
          row.used_at = _utcnow()
          user = db.exec(select(User).where(User.id == row.user_id)).one()
          user.password_hash = self.password.hash(new_password)
          user.failed_login_count = 0
          user.locked_until = None
          user.updated_at = _utcnow()
          db.add(row)
          db.add(user)
          for s in db.exec(
              select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
          ).all():
              s.revoked_at = _utcnow()
              db.add(s)
          db.commit()
          self.audit.log(db, user_id=user.id, event="password.reset_completed", ip=ip, user_agent=ua, metadata={})

      # ---------- password change ----------

      def change_password(
          self,
          db: Session,
          *,
          user: User,
          current_password: str,
          new_password: str,
          current_refresh_token: str | None,
          ip: str | None,
          ua: str | None,
      ) -> None:
          if not self.password.verify(current_password, user.password_hash):
              raise InvalidCredentialsError()
          if len(new_password) < 12:
              raise InvalidCredentialsError()
          user.password_hash = self.password.hash(new_password)
          user.updated_at = _utcnow()
          db.add(user)
          current_hash = self.tokens.hash_refresh(current_refresh_token) if current_refresh_token else None
          for s in db.exec(
              select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
          ).all():
              if current_hash is None or s.refresh_token_hash != current_hash:
                  s.revoked_at = _utcnow()
                  db.add(s)
          db.commit()
          self.audit.log(db, user_id=user.id, event="password.change", ip=ip, user_agent=ua, metadata={})

      # ---------- resend verification ----------

      def resend_verification(self, db: Session, *, email_addr: str, ip: str | None, ua: str | None) -> None:
          normalized = email_addr.strip().lower()
          user = db.exec(select(User).where(User.email == normalized)).first()
          self.audit.log(db, user_id=user.id if user else None, event="user.resend_verification",
                         ip=ip, user_agent=ua, metadata={"email": normalized})
          if user is None or user.email_verified:
              return
          plain = secrets.token_urlsafe(32)
          db.add(
              EmailToken(
                  user_id=user.id,
                  token_hash=_sha256(plain),
                  purpose="verify_email",
                  expires_at=_utcnow() + timedelta(hours=24),
              )
          )
          db.commit()
          self.email.send_verify_email(normalized, plain)
  ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd backend && python -m pytest tests/test_auth_service.py -v`
  Expected: PASS (15 tests)

- [ ] **Step 5: Commit**

  ```bash
  git add backend/services/auth_service.py backend/tests/test_auth_service.py
  git commit -m "feat(auth): add password reset, password change, resend-verification flows"
  ```

---

### Task 3.5: /auth router, dependencies, main.py wiring

- [ ] **Step 1: Write the failing test**

  File: `backend/tests/test_auth_routes.py`

  ```python
  import pytest
  from fastapi.testclient import TestClient
  from sqlmodel import Session, SQLModel, create_engine

  from database import get_db
  from dependencies import get_auth_service, get_email_service
  from main import app
  from services.audit_service import AuditService
  from services.auth_service import AuthService
  from services.email_service import FakeEmailService
  from services.password_service import PasswordService
  from services.token_service import TokenService


  @pytest.fixture
  def client(monkeypatch):
      monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-length!")
      eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
      SQLModel.metadata.create_all(eng)
      fake_email = FakeEmailService()
      svc = AuthService(password=PasswordService(), tokens=TokenService(), email=fake_email, audit=AuditService())

      def _db_override():
          with Session(eng) as db:
              yield db

      app.dependency_overrides[get_db] = _db_override
      app.dependency_overrides[get_auth_service] = lambda: svc
      app.dependency_overrides[get_email_service] = lambda: fake_email
      yield TestClient(app), fake_email
      app.dependency_overrides.clear()


  def test_register_returns_generic_200(client):
      c, _ = client
      res = c.post("/auth/register", json={"email": "r1@example.com", "password": "longpassword12"})
      assert res.status_code == 200
      assert "inbox" in res.json()["message"].lower()


  def test_register_duplicate_email_returns_generic_200_no_second_mail(client):
      c, email = client
      c.post("/auth/register", json={"email": "dup@example.com", "password": "longpassword12"})
      email.sent.clear()
      res = c.post("/auth/register", json={"email": "dup@example.com", "password": "otherlongpass12"})
      assert res.status_code == 200
      assert email.sent == []


  def test_verify_email_then_login(client):
      c, email = client
      c.post("/auth/register", json={"email": "ok@example.com", "password": "longpassword12"})
      token = email.sent[-1][2]
      assert c.post("/auth/verify-email", json={"token": token}).status_code == 200
      res = c.post("/auth/login", json={"email": "ok@example.com", "password": "longpassword12"})
      assert res.status_code == 200
      body = res.json()
      assert "access_token" in body and "refresh_token" in body


  def test_login_wrong_password_401_generic(client):
      c, email = client
      c.post("/auth/register", json={"email": "w@example.com", "password": "longpassword12"})
      token = email.sent[-1][2]
      c.post("/auth/verify-email", json={"token": token})
      res = c.post("/auth/login", json={"email": "w@example.com", "password": "badbadbadbad12"})
      assert res.status_code == 401
      assert res.json()["error"] == "invalid_credentials"


  def test_login_unknown_email_401_generic(client):
      c, _ = client
      res = c.post("/auth/login", json={"email": "nobody@example.com", "password": "longpassword12"})
      assert res.status_code == 401
      assert res.json()["error"] == "invalid_credentials"


  def test_login_unverified_returns_403(client):
      c, _ = client
      c.post("/auth/register", json={"email": "nv@example.com", "password": "longpassword12"})
      res = c.post("/auth/login", json={"email": "nv@example.com", "password": "longpassword12"})
      assert res.status_code == 403
      assert res.json()["error"] == "email_not_verified"


  def test_refresh_rotates_and_old_invalid(client):
      c, email = client
      c.post("/auth/register", json={"email": "rf@example.com", "password": "longpassword12"})
      c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
      tokens = c.post("/auth/login", json={"email": "rf@example.com", "password": "longpassword12"}).json()
      res = c.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
      assert res.status_code == 200
      new_tokens = res.json()
      assert new_tokens["refresh_token"] != tokens["refresh_token"]
      again = c.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
      assert again.status_code == 401


  def test_logout_revokes_current_session(client):
      c, email = client
      c.post("/auth/register", json={"email": "lo@example.com", "password": "longpassword12"})
      c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
      tokens = c.post("/auth/login", json={"email": "lo@example.com", "password": "longpassword12"}).json()
      assert c.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]}).status_code == 200
      again = c.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
      assert again.status_code == 401


  def test_me_returns_profile_when_authenticated(client):
      c, email = client
      c.post("/auth/register", json={"email": "me@example.com", "password": "longpassword12"})
      c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
      tokens = c.post("/auth/login", json={"email": "me@example.com", "password": "longpassword12"}).json()
      res = c.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
      assert res.status_code == 200
      assert res.json()["email"] == "me@example.com"


  def test_me_returns_401_when_no_token(client):
      c, _ = client
      res = c.get("/auth/me")
      assert res.status_code == 401


  def test_password_reset_request_unknown_email_returns_200(client):
      c, email = client
      res = c.post("/auth/password/reset/request", json={"email": "ghost@example.com"})
      assert res.status_code == 200
      assert email.sent == []


  def test_password_reset_confirm_revokes_all_sessions(client):
      c, email = client
      c.post("/auth/register", json={"email": "rs@example.com", "password": "longpassword12"})
      c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
      t1 = c.post("/auth/login", json={"email": "rs@example.com", "password": "longpassword12"}).json()
      t2 = c.post("/auth/login", json={"email": "rs@example.com", "password": "longpassword12"}).json()
      email.sent.clear()
      c.post("/auth/password/reset/request", json={"email": "rs@example.com"})
      reset_token = email.sent[-1][2]
      res = c.post("/auth/password/reset/confirm", json={"token": reset_token, "new_password": "newlongpassword34"})
      assert res.status_code == 200
      assert c.post("/auth/refresh", json={"refresh_token": t1["refresh_token"]}).status_code == 401
      assert c.post("/auth/refresh", json={"refresh_token": t2["refresh_token"]}).status_code == 401
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd backend && python -m pytest tests/test_auth_routes.py -v`
  Expected: FAIL — `/auth/*` routes and `get_auth_service` do not exist yet.

- [ ] **Step 3: Implement**

  Extend `backend/dependencies.py`:

  ```python
  from uuid import UUID

  from fastapi import Depends, HTTPException, Request, status
  from sqlmodel import Session, select

  from database import get_db
  from models.auth import User
  from services.auth_service import AuthService


  @lru_cache(maxsize=1)
  def _auth_service_singleton() -> AuthService:
      return AuthService(
          password=get_password_service(),
          tokens=get_token_service(),
          email=get_email_service(),
          audit=get_audit_service(),
      )


  def get_auth_service() -> AuthService:
      return _auth_service_singleton()


  def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
      state_user = getattr(request.state, "user", None)
      if not state_user:
          return None
      try:
          uid = UUID(state_user["id"])
      except (KeyError, ValueError):
          return None
      return db.exec(select(User).where(User.id == uid)).first()


  def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
      if user is None:
          raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication_required")
      return user


  def get_admin_user(user: User = Depends(get_current_user)) -> User:
      if user.role != "admin":
          raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_only")
      return user
  ```

  File: `backend/routers/auth.py`

  ```python
  """HTTP layer for /auth/* endpoints."""
  from __future__ import annotations

  from fastapi import APIRouter, Depends, Request, Response, status
  from pydantic import BaseModel, EmailStr, Field
  from sqlmodel import Session

  from database import get_db
  from dependencies import get_auth_service, get_current_user
  from exceptions import (
      AccountLockedError,
      EmailNotVerifiedError,
      InvalidCredentialsError,
      TokenInvalidError,
  )
  from models.auth import User
  from services.auth_service import AuthService

  router = APIRouter(prefix="/auth", tags=["auth"])

  GENERIC_REGISTER_MSG = "If the email is new, check your inbox to verify."


  class RegisterIn(BaseModel):
      email: EmailStr
      password: str = Field(min_length=12)


  class VerifyIn(BaseModel):
      token: str


  class LoginIn(BaseModel):
      email: EmailStr
      password: str


  class RefreshIn(BaseModel):
      refresh_token: str


  class LogoutIn(BaseModel):
      refresh_token: str


  class ResetRequestIn(BaseModel):
      email: EmailStr


  class ResetConfirmIn(BaseModel):
      token: str
      new_password: str = Field(min_length=12)


  class PasswordChangeIn(BaseModel):
      current_password: str
      new_password: str = Field(min_length=12)
      current_refresh_token: str | None = None


  class ResendIn(BaseModel):
      email: EmailStr


  def _client(request: Request) -> tuple[str | None, str | None]:
      ip = request.client.host if request.client else None
      ua = request.headers.get("user-agent")
      return ip, ua


  def _err(exc: Exception, response: Response) -> dict:
      if isinstance(exc, InvalidCredentialsError):
          response.status_code = status.HTTP_401_UNAUTHORIZED
          return {"error": "invalid_credentials"}
      if isinstance(exc, EmailNotVerifiedError):
          response.status_code = status.HTTP_403_FORBIDDEN
          return {"error": "email_not_verified"}
      if isinstance(exc, AccountLockedError):
          response.status_code = status.HTTP_423_LOCKED
          return {"error": "account_locked", "locked_until": exc.locked_until}
      if isinstance(exc, TokenInvalidError):
          response.status_code = status.HTTP_401_UNAUTHORIZED
          return {"error": "token_invalid"}
      raise exc


  @router.post("/register")
  def register(body: RegisterIn, request: Request, db: Session = Depends(get_db),
               svc: AuthService = Depends(get_auth_service)):
      ip, ua = _client(request)
      try:
          svc.register(db, email_addr=body.email, password=body.password, ip=ip, ua=ua)
      except ValueError:
          pass
      return {"message": GENERIC_REGISTER_MSG}


  @router.post("/verify-email")
  def verify_email(body: VerifyIn, request: Request, response: Response,
                   db: Session = Depends(get_db), svc: AuthService = Depends(get_auth_service)):
      ip, ua = _client(request)
      try:
          svc.verify_email(db, token=body.token, ip=ip, ua=ua)
      except TokenInvalidError as e:
          return _err(e, response)
      return {"verified": True}


  @router.post("/login")
  def login(body: LoginIn, request: Request, response: Response,
            db: Session = Depends(get_db), svc: AuthService = Depends(get_auth_service)):
      ip, ua = _client(request)
      try:
          return svc.login(db, email_addr=body.email, password=body.password, ip=ip, ua=ua)
      except (InvalidCredentialsError, EmailNotVerifiedError, AccountLockedError) as e:
          return _err(e, response)


  @router.post("/refresh")
  def refresh(body: RefreshIn, request: Request, response: Response,
              db: Session = Depends(get_db), svc: AuthService = Depends(get_auth_service)):
      ip, ua = _client(request)
      try:
          return svc.refresh(db, refresh_token=body.refresh_token, ip=ip, ua=ua)
      except TokenInvalidError as e:
          return _err(e, response)


  @router.post("/logout")
  def logout(body: LogoutIn, request: Request,
             db: Session = Depends(get_db), svc: AuthService = Depends(get_auth_service)):
      ip, ua = _client(request)
      svc.logout(db, refresh_token=body.refresh_token, ip=ip, ua=ua)
      return {"ok": True}


  @router.get("/me")
  def me(user: User = Depends(get_current_user)):
      return {
          "id": str(user.id),
          "email": user.email,
          "role": user.role,
          "totp_enabled": user.totp_enabled,
          "created_at": user.created_at.isoformat(),
      }


  @router.post("/password/reset/request")
  def reset_request(body: ResetRequestIn, request: Request,
                    db: Session = Depends(get_db), svc: AuthService = Depends(get_auth_service)):
      ip, ua = _client(request)
      svc.request_password_reset(db, email_addr=body.email, ip=ip, ua=ua)
      return {"message": GENERIC_REGISTER_MSG}


  @router.post("/password/reset/confirm")
  def reset_confirm(body: ResetConfirmIn, request: Request, response: Response,
                    db: Session = Depends(get_db), svc: AuthService = Depends(get_auth_service)):
      ip, ua = _client(request)
      try:
          svc.confirm_password_reset(db, token=body.token, new_password=body.new_password, ip=ip, ua=ua)
      except TokenInvalidError as e:
          return _err(e, response)
      return {"ok": True}


  @router.post("/password/change")
  def password_change(body: PasswordChangeIn, request: Request, response: Response,
                      user: User = Depends(get_current_user),
                      db: Session = Depends(get_db), svc: AuthService = Depends(get_auth_service)):
      ip, ua = _client(request)
      try:
          svc.change_password(
              db,
              user=user,
              current_password=body.current_password,
              new_password=body.new_password,
              current_refresh_token=body.current_refresh_token,
              ip=ip,
              ua=ua,
          )
      except InvalidCredentialsError as e:
          return _err(e, response)
      return {"ok": True}


  @router.post("/resend-verification")
  def resend(body: ResendIn, request: Request,
             db: Session = Depends(get_db), svc: AuthService = Depends(get_auth_service)):
      ip, ua = _client(request)
      svc.resend_verification(db, email_addr=body.email, ip=ip, ua=ua)
      return {"message": GENERIC_REGISTER_MSG}
  ```

  Modify `backend/main.py`:
  - DELETE the import and `app.add_middleware(APIKeyAuthMiddleware)` line.
  - ADD:
    ```python
    from middleware.auth import JWTAuthMiddleware
    from middleware.service_token import ServiceTokenMiddleware
    from routers import auth as auth_router

    app.add_middleware(JWTAuthMiddleware)
    app.add_middleware(ServiceTokenMiddleware)
    # CORS must already be added after these two so that Starlette's LIFO wrapping
    # yields: CORS (outer) -> ServiceTokenMiddleware -> JWTAuthMiddleware (inner).
    # If CORS was added earlier in the file, move it to AFTER these two lines.

    app.include_router(auth_router.router)
    ```

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd backend && python -m pytest tests/test_auth_routes.py -v`
  Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

  ```bash
  git add backend/routers/auth.py backend/dependencies.py backend/main.py backend/tests/test_auth_routes.py
  git commit -m "feat(auth): wire /auth router, current-user dependencies, and middleware order"
  ```

---

### Task 3.6: Enumeration parity and login timing guard

- [ ] **Step 1: Write the failing test**

  File: `backend/tests/test_security_enumeration.py`

  ```python
  import time

  import pytest
  from fastapi.testclient import TestClient
  from sqlmodel import Session, SQLModel, create_engine

  from database import get_db
  from dependencies import get_auth_service, get_email_service
  from main import app
  from services.audit_service import AuditService
  from services.auth_service import AuthService
  from services.email_service import FakeEmailService
  from services.password_service import PasswordService
  from services.token_service import TokenService


  @pytest.fixture
  def client(monkeypatch):
      monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-length!")
      eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
      SQLModel.metadata.create_all(eng)
      fake_email = FakeEmailService()
      svc = AuthService(password=PasswordService(), tokens=TokenService(), email=fake_email, audit=AuditService())

      def _db_override():
          with Session(eng) as db:
              yield db

      app.dependency_overrides[get_db] = _db_override
      app.dependency_overrides[get_auth_service] = lambda: svc
      app.dependency_overrides[get_email_service] = lambda: fake_email
      yield TestClient(app), fake_email
      app.dependency_overrides.clear()


  def test_register_and_duplicate_return_same_shape(client):
      c, _ = client
      r1 = c.post("/auth/register", json={"email": "a@example.com", "password": "longpassword12"})
      r2 = c.post("/auth/register", json={"email": "a@example.com", "password": "longpassword12"})
      assert r1.status_code == r2.status_code == 200
      assert r1.json() == r2.json()


  def test_reset_request_and_unknown_return_same_shape(client):
      c, email = client
      c.post("/auth/register", json={"email": "x@example.com", "password": "longpassword12"})
      c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
      r_known = c.post("/auth/password/reset/request", json={"email": "x@example.com"})
      r_unknown = c.post("/auth/password/reset/request", json={"email": "ghost@example.com"})
      assert r_known.status_code == r_unknown.status_code == 200
      assert r_known.json() == r_unknown.json()


  def test_login_wrong_email_vs_wrong_password_same_shape(client):
      c, email = client
      c.post("/auth/register", json={"email": "t@example.com", "password": "longpassword12"})
      c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
      r_wrong_email = c.post("/auth/login", json={"email": "no@example.com", "password": "longpassword12"})
      r_wrong_pw = c.post("/auth/login", json={"email": "t@example.com", "password": "wrongpassword12"})
      assert r_wrong_email.status_code == r_wrong_pw.status_code == 401
      assert r_wrong_email.json() == r_wrong_pw.json()


  def test_no_user_enumeration_timing(client):
      """Mean timing gap between unknown-email and wrong-password must be < 50ms."""
      c, email = client
      c.post("/auth/register", json={"email": "tim@example.com", "password": "longpassword12"})
      c.post("/auth/verify-email", json={"token": email.sent[-1][2]})

      for _ in range(3):
          c.post("/auth/login", json={"email": "tim@example.com", "password": "wrongwrongwrong12"})
          c.post("/auth/login", json={"email": "ghost@example.com", "password": "wrongwrongwrong12"})

      runs = 10
      t_known = 0.0
      t_unknown = 0.0
      for _ in range(runs):
          start = time.perf_counter()
          c.post("/auth/login", json={"email": "tim@example.com", "password": "wrongwrongwrong12"})
          t_known += time.perf_counter() - start
          start = time.perf_counter()
          c.post("/auth/login", json={"email": "ghost@example.com", "password": "wrongwrongwrong12"})
          t_unknown += time.perf_counter() - start

      avg_known = t_known / runs
      avg_unknown = t_unknown / runs
      assert abs(avg_known - avg_unknown) < 0.050, f"timing gap too large: {avg_known=} {avg_unknown=}"
  ```

- [ ] **Step 2: Run test to verify it fails (or passes)**

  Run: `cd backend && python -m pytest tests/test_security_enumeration.py -v`
  Expected: Parity tests PASS; timing test should PASS because the dummy-hash equalizer is already in AuthService.login. If the timing test fails, the likely cause is that the unknown-email branch commits an extra audit row while the wrong-password branch also commits one — both paths should already commit exactly once. No further implementation in this task if green.

- [ ] **Step 3: Implement**

  No implementation needed if tests pass. If the timing test fails, ensure `AuthService.login` does NOT short-circuit the dummy `password.verify(password, _DUMMY_HASH)` call on the unknown-email branch — it must run the same argon2 work as the real verify.

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd backend && python -m pytest tests/test_security_enumeration.py -v`
  Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

  ```bash
  git add backend/tests/test_security_enumeration.py
  git commit -m "test(auth): add enumeration parity and login timing guard"
  ```

---

### Task 3.7: Rate limit guard on /auth/login (slowapi)

- [ ] **Step 1: Write the failing test**

  Append to `backend/tests/test_auth_routes.py`:

  ```python
  def test_rate_limit_login_5_per_min(client):
      """slowapi limit 5/minute/IP on /auth/login — 6th call returns 429."""
      c, email = client
      c.post("/auth/register", json={"email": "rl@example.com", "password": "longpassword12"})
      c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
      for _ in range(5):
          c.post("/auth/login", json={"email": "rl@example.com", "password": "wrongpassword12"})
      res = c.post("/auth/login", json={"email": "rl@example.com", "password": "wrongpassword12"})
      assert res.status_code == 429
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `cd backend && python -m pytest tests/test_auth_routes.py::test_rate_limit_login_5_per_min -v`
  Expected: FAIL — 6th call returns 401, not 429 (no limiter decorator yet).

- [ ] **Step 3: Implement**

  In `backend/routers/auth.py`, import the existing slowapi limiter (already wired in `middleware/rate_limiter.py` and `main.py`) and decorate the endpoints:

  ```python
  from middleware.rate_limiter import limiter  # reuse existing singleton

  @router.post("/register")
  @limiter.limit("3/minute")
  def register(request: Request, body: RegisterIn, ...):
      ...

  @router.post("/login")
  @limiter.limit("5/minute")
  def login(request: Request, body: LoginIn, response: Response, ...):
      ...

  @router.post("/password/reset/request")
  @limiter.limit("3/hour")
  def reset_request(request: Request, body: ResetRequestIn, ...):
      ...

  @router.post("/refresh")
  @limiter.limit("30/minute")
  def refresh(request: Request, body: RefreshIn, response: Response, ...):
      ...
  ```

  `slowapi` requires the first positional param to be named `request: Request`. Reorder the function signatures so `request` comes first. Ensure `main.py` already has `app.state.limiter = limiter` and `app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)` — if not, add them next to the middleware wiring.

- [ ] **Step 4: Run test to verify it passes**

  Run: `cd backend && python -m pytest tests/test_auth_routes.py::test_rate_limit_login_5_per_min -v`
  Expected: PASS

- [ ] **Step 5: Commit**

  ```bash
  git add backend/routers/auth.py backend/main.py backend/tests/test_auth_routes.py
  git commit -m "feat(auth): enforce slowapi rate limits on login/register/reset/refresh"
  ```

---

### Task 3.8: Opus Gate 3A — Security sweep (auth routes)

**Security Review (Opus subagent)**

Run this Opus security review before moving to Phase 4. Copy-paste the invocation block below into a fresh Claude Code session:

````
Agent({
  subagent_type: "general-purpose",
  model: "opus",
  description: "Opus security review: auth routes sweep",
  prompt: "Review backend/services/auth_service.py and backend/routers/auth.py for the following threats. Produce a structured report with severity (critical/high/medium/low), file:line, attack scenario, and proposed patch as a unified diff for each finding.\n\n1. Refresh-rotation race condition: Two concurrent POST /auth/refresh calls arrive with the same refresh_token. Walk through the SQL ordering and confirm exactly ONE succeeds and the other triggers reuse detection. If the current implementation uses select+update-in-Python, recommend moving to an atomic `UPDATE user_sessions SET revoked_at=now() WHERE refresh_token_hash=? AND revoked_at IS NULL RETURNING *` and show the exact patch.\n\n2. Login timing attack: Confirm the unknown-email branch in AuthService.login runs password.verify against the dummy argon2 hash BEFORE raising InvalidCredentialsError, with no additional asymmetric DB work. Measure whether early `select(User)` miss versus an argon2 verify introduces >5ms asymmetry. Recommend a fix if so.\n\n3. Lockout counter transactional correctness: With concurrent bad-password attempts, can failed_login_count skip past 10 without triggering the lockout, or trigger it multiple times? Recommend an atomic `UPDATE users SET failed_login_count = failed_login_count + 1, locked_until = CASE ... END WHERE id=? RETURNING failed_login_count, locked_until`.\n\n4. verify_email single-use atomicity: Confirm a replayed POST /auth/verify-email with the same token cannot succeed twice under concurrency. Recommend replacing select+update with a single atomic `UPDATE email_tokens SET used_at=now() WHERE token_hash=? AND used_at IS NULL AND expires_at > now() RETURNING user_id`.\n\n5. Generic-error parity: Confirm wrong-email / wrong-password / unverified-email status codes match the spec (401/401/403), and that wrong-email and wrong-password return identical 401 bodies. Confirm register and reset-request always return identical 200 body regardless of email existence.\n\n6. Reuse detection correctness: Confirm an already-revoked refresh_token revokes all OTHER sessions for that user, writes `session.refresh_reuse_detected` exactly once, and returns 401 with {error: 'token_invalid'}.\n\n7. JWT middleware leak: Confirm JWTAuthMiddleware never returns 401 itself, skips /health and /cron/*, and that an invalid token always sets request.state.user = None (not a cached previous value).\n\n8. Password-change session revocation: Confirm change_password revokes ALL sessions EXCEPT the one matching current_refresh_token, and that when current_refresh_token is None all sessions are revoked.\n\nFor each finding include (a) exact lines quoted, (b) attack scenario, (c) concrete patch as unified diff. End the report with a one-paragraph green-light or red-light verdict for Phase 4."
})
````

- [ ] **Step 1: Invoke Opus gate (copy the block above).**
- [ ] **Step 2: Apply each Opus finding as a separate follow-up commit with message** `fix(auth): address opus gate 3A <short description>`.
- [ ] **Step 3: Re-run all phase 3 tests.**
  Run: `cd backend && python -m pytest tests/test_auth_service.py tests/test_auth_routes.py tests/test_auth_middleware.py tests/test_service_token_middleware.py tests/test_security_enumeration.py -v`
  Expected: PASS (full phase 3 suite, ~30 tests)
- [ ] **Step 4: Tag the phase.**
  ```bash
  git tag phase-3-complete
  ```
## Phase 4: 2FA (TOTP)

**Goal:** Add TOTP setup/enable/disable routes plus a two-step login challenge flow, using an atomic Redis challenge store.

**Files:**
- Create: `backend/services/challenge_store.py`
- Create: `backend/tests/test_challenge_store.py`
- Create: `backend/tests/test_2fa_routes.py`
- Modify: `backend/routers/auth.py`
- Modify: `backend/services/auth_service.py`
- Modify: `backend/dependencies.py`

### Task 4.1: Challenge store (Redis GETDEL wrapper)

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_challenge_store.py
  import fakeredis
  import pytest

  from services.challenge_store import ChallengeStore


  @pytest.fixture
  def store():
      client = fakeredis.FakeStrictRedis(decode_responses=True)
      return ChallengeStore(client)


  def test_put_then_consume_returns_value(store):
      store.put("abc123", "user-uuid-1", ttl_seconds=300)
      assert store.consume("abc123") == "user-uuid-1"


  def test_consume_missing_returns_none(store):
      assert store.consume("nope") is None
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_challenge_store.py::test_put_then_consume_returns_value -v`
  Expected: FAIL with `ModuleNotFoundError: No module named 'services.challenge_store'`
- [ ] **Step 3: Implement**
  ```python
  # backend/services/challenge_store.py
  """Redis-backed single-use challenge store for 2FA login flow."""
  from __future__ import annotations

  from typing import Protocol


  class RedisLike(Protocol):
      def set(self, name: str, value: str, ex: int | None = ..., nx: bool = ...) -> bool | None: ...
      def execute_command(self, *args: object) -> object: ...


  class ChallengeStore:
      """Stores short-lived 2FA challenge_id -> user_id mappings.

      consume() is atomic (GETDEL) so concurrent callers cannot both succeed.
      """

      PREFIX = "auth:2fa:challenge:"

      def __init__(self, client: RedisLike) -> None:
          self._client = client

      def put(self, challenge_id: str, user_id: str, ttl_seconds: int = 300) -> None:
          self._client.set(self._key(challenge_id), user_id, ex=ttl_seconds, nx=True)

      def consume(self, challenge_id: str) -> str | None:
          raw = self._client.execute_command("GETDEL", self._key(challenge_id))
          if raw is None:
              return None
          if isinstance(raw, bytes):
              return raw.decode("utf-8")
          return str(raw)

      def _key(self, challenge_id: str) -> str:
          return f"{self.PREFIX}{challenge_id}"
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_challenge_store.py::test_put_then_consume_returns_value -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/services/challenge_store.py backend/tests/test_challenge_store.py
  git commit -m "feat(auth): add Redis challenge store for 2FA login flow"
  ```

### Task 4.2: Challenge store GETDEL atomicity

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_challenge_store.py (append)
  def test_challenge_store_getdel_atomic(store):
      store.put("single", "user-uuid-42", ttl_seconds=300)
      first = store.consume("single")
      second = store.consume("single")
      assert first == "user-uuid-42"
      assert second is None
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_challenge_store.py::test_challenge_store_getdel_atomic -v`
  Expected: PASS already (fakeredis supports GETDEL). If FAIL with `unknown command GETDEL`, upgrade fakeredis to >=2.20 in `requirements-dev.txt` and rerun.
- [ ] **Step 3: Implement**
  Nothing to implement — verifies the `execute_command("GETDEL", ...)` path is truly single-use.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_challenge_store.py -v`
  Expected: PASS (3 tests)
- [ ] **Step 5: Commit**
  ```bash
  git add backend/tests/test_challenge_store.py
  git commit -m "test(auth): verify challenge store GETDEL single-use atomicity"
  ```

### Task 4.3: Inject challenge store singleton

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_2fa_routes.py
  import pytest
  from fastapi.testclient import TestClient

  from dependencies import get_challenge_store
  from main import app


  def test_get_challenge_store_dependency_resolves():
      assert get_challenge_store() is not None
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_get_challenge_store_dependency_resolves -v`
  Expected: FAIL with `ImportError: cannot import name 'get_challenge_store'`
- [ ] **Step 3: Implement**
  ```python
  # backend/dependencies.py (append)
  from functools import lru_cache

  from services.challenge_store import ChallengeStore


  @lru_cache(maxsize=1)
  def get_challenge_store() -> ChallengeStore:
      from redis_client import get_redis  # existing singleton used by rate limiter

      return ChallengeStore(get_redis())
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_get_challenge_store_dependency_resolves -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/dependencies.py backend/tests/test_2fa_routes.py
  git commit -m "feat(auth): expose get_challenge_store DI singleton"
  ```

### Task 4.4: 2FA setup returns secret + URI, does not enable

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_2fa_routes.py (append)
  from tests.helpers import register_and_login, get_user, auth_headers


  def test_2fa_setup_returns_secret_and_uri_but_not_enabled(client):
      tokens = register_and_login(client, "alice@example.com", "correct horse battery 1")
      res = client.post("/auth/2fa/setup", headers=auth_headers(tokens))
      assert res.status_code == 200
      body = res.json()
      assert "secret" in body and len(body["secret"]) >= 16
      assert body["provisioning_uri"].startswith("otpauth://totp/")
      user = get_user(client, "alice@example.com")
      assert user.totp_enabled is False
      assert user.totp_secret is not None
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_2fa_setup_returns_secret_and_uri_but_not_enabled -v`
  Expected: FAIL with `404 Not Found` (route does not exist yet)
- [ ] **Step 3: Implement**
  ```python
  # backend/services/auth_service.py (append method on AuthService)
  def start_2fa_setup(self, db: Session, user: User) -> dict[str, str]:
      secret = self.totp.generate_secret()
      user.totp_secret = self.totp.encrypt(secret)
      user.totp_enabled = False
      db.add(user)
      db.commit()
      return {
          "secret": secret,
          "provisioning_uri": self.totp.provisioning_uri(secret, user.email),
      }
  ```
  ```python
  # backend/routers/auth.py (append)
  @router.post("/2fa/setup")
  def twofa_setup(
      current_user: User = Depends(get_current_user),
      auth: AuthService = Depends(get_auth_service),
      db: Session = Depends(get_db),
  ) -> dict[str, str]:
      return auth.start_2fa_setup(db, current_user)
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_2fa_setup_returns_secret_and_uri_but_not_enabled -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/services/auth_service.py backend/routers/auth.py backend/tests/test_2fa_routes.py
  git commit -m "feat(auth): add POST /auth/2fa/setup route"
  ```

### Task 4.5: Setup persists encrypted secret

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_2fa_routes.py (append)
  def test_2fa_setup_persists_encrypted_secret(client, totp_service):
      tokens = register_and_login(client, "bob@example.com", "correct horse battery 2")
      res = client.post("/auth/2fa/setup", headers=auth_headers(tokens))
      secret_plain = res.json()["secret"]
      user = get_user(client, "bob@example.com")
      assert user.totp_secret != secret_plain  # must be encrypted
      assert totp_service.decrypt(user.totp_secret) == secret_plain
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_2fa_setup_persists_encrypted_secret -v`
  Expected: PASS already (implemented in 4.4). If FAIL because of fixture wiring, add a `totp_service` fixture to `backend/tests/conftest.py` returning `get_totp_service()`.
- [ ] **Step 3: Implement**
  Add fixture only if not present:
  ```python
  # backend/tests/conftest.py (append)
  @pytest.fixture
  def totp_service():
      from dependencies import get_totp_service
      return get_totp_service()
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_2fa_setup_persists_encrypted_secret -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/tests/conftest.py backend/tests/test_2fa_routes.py
  git commit -m "test(auth): assert 2fa setup persists encrypted secret"
  ```

### Task 4.6: Enable rejects wrong code

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_2fa_routes.py (append)
  def test_2fa_enable_rejects_wrong_code(client):
      tokens = register_and_login(client, "carol@example.com", "correct horse battery 3")
      client.post("/auth/2fa/setup", headers=auth_headers(tokens))
      res = client.post("/auth/2fa/enable", json={"code": "000000"}, headers=auth_headers(tokens))
      assert res.status_code == 400
      user = get_user(client, "carol@example.com")
      assert user.totp_enabled is False
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_2fa_enable_rejects_wrong_code -v`
  Expected: FAIL with `404 Not Found`
- [ ] **Step 3: Implement**
  ```python
  # backend/services/auth_service.py (append)
  def enable_2fa(self, db: Session, user: User, code: str, *, ip: str, ua: str) -> None:
      if not user.totp_secret:
          raise HTTPException(status_code=400, detail="2FA not initialized")
      secret = self.totp.decrypt(user.totp_secret)
      if not self.totp.verify(secret, code, valid_window=1):
          raise HTTPException(status_code=400, detail="Invalid code")
      user.totp_enabled = True
      db.add(user)
      # Revoke OTHER sessions: keep current (refresh token hash of the request)
      current_hash = getattr(user, "_current_session_hash", None)
      q = db.query(UserSession).filter(
          UserSession.user_id == user.id,
          UserSession.revoked_at.is_(None),
      )
      if current_hash:
          q = q.filter(UserSession.refresh_token_hash != current_hash)
      for s in q.all():
          s.revoked_at = utcnow()
          db.add(s)
      db.commit()
      self.audit.log(db, user_id=user.id, event="user.2fa_enabled", ip=ip, user_agent=ua, metadata={})
  ```
  ```python
  # backend/routers/auth.py (append)
  class TwoFaEnableBody(BaseModel):
      code: str


  @router.post("/2fa/enable")
  def twofa_enable(
      body: TwoFaEnableBody,
      request: Request,
      current_user: User = Depends(get_current_user),
      auth: AuthService = Depends(get_auth_service),
      db: Session = Depends(get_db),
  ) -> dict[str, str]:
      auth.enable_2fa(
          db,
          current_user,
          body.code,
          ip=request.client.host if request.client else "",
          ua=request.headers.get("user-agent", ""),
      )
      return {"status": "ok"}
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_2fa_enable_rejects_wrong_code -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/services/auth_service.py backend/routers/auth.py backend/tests/test_2fa_routes.py
  git commit -m "feat(auth): add POST /auth/2fa/enable with code verification"
  ```

### Task 4.7: Enable success flips flag

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_2fa_routes.py (append)
  import pyotp


  def test_2fa_enable_success_flips_flag(client):
      tokens = register_and_login(client, "dave@example.com", "correct horse battery 4")
      setup = client.post("/auth/2fa/setup", headers=auth_headers(tokens)).json()
      code = pyotp.TOTP(setup["secret"]).now()
      res = client.post("/auth/2fa/enable", json={"code": code}, headers=auth_headers(tokens))
      assert res.status_code == 200
      user = get_user(client, "dave@example.com")
      assert user.totp_enabled is True
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_2fa_enable_success_flips_flag -v`
  Expected: PASS (implementation from 4.6 covers it). If FAIL, inspect why `pyotp.TOTP(...).now()` is rejected — likely clock drift in fixture.
- [ ] **Step 3: Implement**
  None.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_2fa_enable_success_flips_flag -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/tests/test_2fa_routes.py
  git commit -m "test(auth): verify 2fa enable success flips totp_enabled flag"
  ```

### Task 4.8: Enable revokes other sessions, keeps current

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_2fa_routes.py (append)
  def test_2fa_enable_revokes_other_sessions_keeps_current(client, db_session):
      # login twice -> two sessions
      register_and_login(client, "eve@example.com", "correct horse battery 5")
      first = client.post("/auth/login", json={"email": "eve@example.com", "password": "correct horse battery 5"}).json()
      second = client.post("/auth/login", json={"email": "eve@example.com", "password": "correct horse battery 5"}).json()
      # setup + enable using the SECOND session
      setup = client.post("/auth/2fa/setup", headers=auth_headers(second)).json()
      code = pyotp.TOTP(setup["secret"]).now()
      client.post("/auth/2fa/enable", json={"code": code}, headers=auth_headers(second))
      # refresh with the FIRST session -> must be revoked
      res = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
      assert res.status_code == 401
      # refresh with the SECOND -> still alive
      res2 = client.post("/auth/refresh", json={"refresh_token": second["refresh_token"]})
      assert res2.status_code == 200
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_2fa_enable_revokes_other_sessions_keeps_current -v`
  Expected: FAIL — current session tracking not yet threaded into `enable_2fa`. Error: first session still refreshes OK.
- [ ] **Step 3: Implement**
  Thread the current session hash from the request into the user object before calling `enable_2fa`:
  ```python
  # backend/routers/auth.py (modify twofa_enable)
  @router.post("/2fa/enable")
  def twofa_enable(
      body: TwoFaEnableBody,
      request: Request,
      current_user: User = Depends(get_current_user),
      auth: AuthService = Depends(get_auth_service),
      db: Session = Depends(get_db),
  ) -> dict[str, str]:
      current_user._current_session_hash = getattr(request.state, "session_hash", None)
      auth.enable_2fa(
          db,
          current_user,
          body.code,
          ip=request.client.host if request.client else "",
          ua=request.headers.get("user-agent", ""),
      )
      return {"status": "ok"}
  ```
  And in `backend/middleware/auth.py`, when the access token is validated, also look up and store the active refresh-session hash on `request.state.session_hash` (if available — may be None on pure-access-token requests; in that case revoke ALL to be safe).
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_2fa_enable_revokes_other_sessions_keeps_current -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/routers/auth.py backend/middleware/auth.py backend/tests/test_2fa_routes.py
  git commit -m "feat(auth): revoke other sessions on 2fa enable, keep current"
  ```

### Task 4.9: Disable requires both password and code

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_2fa_routes.py (append)
  def _enable_2fa(client, email, password):
      tokens = register_and_login(client, email, password)
      setup = client.post("/auth/2fa/setup", headers=auth_headers(tokens)).json()
      code = pyotp.TOTP(setup["secret"]).now()
      client.post("/auth/2fa/enable", json={"code": code}, headers=auth_headers(tokens))
      return tokens, setup["secret"]


  def test_2fa_disable_requires_password_and_code(client):
      tokens, secret = _enable_2fa(client, "frank@example.com", "correct horse battery 6")
      # missing code
      res = client.post("/auth/2fa/disable", json={"current_password": "correct horse battery 6"}, headers=auth_headers(tokens))
      assert res.status_code == 422
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_2fa_disable_requires_password_and_code -v`
  Expected: FAIL with `404 Not Found`
- [ ] **Step 3: Implement**
  ```python
  # backend/services/auth_service.py (append)
  def disable_2fa(
      self,
      db: Session,
      user: User,
      current_password: str,
      code: str,
      *,
      ip: str,
      ua: str,
  ) -> None:
      pw_ok = self.password.verify(current_password, user.password_hash)
      secret = self.totp.decrypt(user.totp_secret) if user.totp_secret else ""
      code_ok = bool(secret) and self.totp.verify(secret, code, valid_window=1)
      if not (pw_ok and code_ok):
          raise HTTPException(status_code=400, detail="Verification failed")
      user.totp_secret = None
      user.totp_enabled = False
      db.add(user)
      for s in db.query(UserSession).filter(
          UserSession.user_id == user.id,
          UserSession.revoked_at.is_(None),
      ).all():
          s.revoked_at = utcnow()
          db.add(s)
      db.commit()
      self.audit.log(db, user_id=user.id, event="user.2fa_disabled", ip=ip, user_agent=ua, metadata={})
  ```
  ```python
  # backend/routers/auth.py (append)
  class TwoFaDisableBody(BaseModel):
      current_password: str
      code: str


  @router.post("/2fa/disable")
  def twofa_disable(
      body: TwoFaDisableBody,
      request: Request,
      current_user: User = Depends(get_current_user),
      auth: AuthService = Depends(get_auth_service),
      db: Session = Depends(get_db),
  ) -> dict[str, str]:
      auth.disable_2fa(
          db,
          current_user,
          body.current_password,
          body.code,
          ip=request.client.host if request.client else "",
          ua=request.headers.get("user-agent", ""),
      )
      return {"status": "ok"}
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_2fa_disable_requires_password_and_code -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/services/auth_service.py backend/routers/auth.py backend/tests/test_2fa_routes.py
  git commit -m "feat(auth): add POST /auth/2fa/disable with dual-factor check"
  ```

### Task 4.10: Disable wrong password / wrong code both rejected with generic 400

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_2fa_routes.py (append)
  def test_2fa_disable_wrong_password_rejected(client):
      tokens, secret = _enable_2fa(client, "greta@example.com", "correct horse battery 7")
      res = client.post(
          "/auth/2fa/disable",
          json={"current_password": "wrong", "code": pyotp.TOTP(secret).now()},
          headers=auth_headers(tokens),
      )
      assert res.status_code == 400
      assert res.json()["detail"] == "Verification failed"


  def test_2fa_disable_wrong_code_rejected(client):
      tokens, secret = _enable_2fa(client, "hank@example.com", "correct horse battery 8")
      res = client.post(
          "/auth/2fa/disable",
          json={"current_password": "correct horse battery 8", "code": "000000"},
          headers=auth_headers(tokens),
      )
      assert res.status_code == 400
      assert res.json()["detail"] == "Verification failed"
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py -k "disable_wrong" -v`
  Expected: PASS (covered by 4.9). If FAIL, message differs — align message with `"Verification failed"`.
- [ ] **Step 3: Implement**
  None (covered).
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py -k "disable_wrong" -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/tests/test_2fa_routes.py
  git commit -m "test(auth): verify 2fa disable does not leak which factor failed"
  ```

### Task 4.11: Disable success revokes ALL sessions

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_2fa_routes.py (append)
  def test_2fa_disable_success_revokes_all_sessions(client):
      tokens, secret = _enable_2fa(client, "ivan@example.com", "correct horse battery 9")
      res = client.post(
          "/auth/2fa/disable",
          json={"current_password": "correct horse battery 9", "code": pyotp.TOTP(secret).now()},
          headers=auth_headers(tokens),
      )
      assert res.status_code == 200
      refresh = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
      assert refresh.status_code == 401
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_2fa_disable_success_revokes_all_sessions -v`
  Expected: PASS
- [ ] **Step 3: Implement**
  None.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_2fa_disable_success_revokes_all_sessions -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/tests/test_2fa_routes.py
  git commit -m "test(auth): verify 2fa disable revokes all sessions"
  ```

### Task 4.12: Login with 2FA returns challenge, no tokens

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_2fa_routes.py (append)
  def test_login_with_2fa_returns_challenge_no_cookies(client):
      _enable_2fa(client, "jane@example.com", "correct horse battery 10")
      res = client.post("/auth/login", json={"email": "jane@example.com", "password": "correct horse battery 10"})
      assert res.status_code == 200
      body = res.json()
      assert body["step"] == "2fa_required"
      assert "challenge_id" in body
      assert "access_token" not in body
      assert "refresh_token" not in body
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_login_with_2fa_returns_challenge_no_cookies -v`
  Expected: FAIL — current login returns tokens unconditionally
- [ ] **Step 3: Implement**
  ```python
  # backend/services/auth_service.py (modify login to branch on totp_enabled)
  def login(self, db, email, password, *, ip, ua):
      user = self._authenticate(db, email, password, ip=ip, ua=ua)  # Phase 3 helper
      if user.totp_enabled:
          import secrets as _secrets
          challenge_id = _secrets.token_urlsafe(24)
          self.challenges.put(challenge_id, str(user.id), ttl_seconds=300)
          self.audit.log(db, user_id=user.id, event="login.2fa_challenge_issued", ip=ip, user_agent=ua, metadata={})
          return {"step": "2fa_required", "challenge_id": challenge_id}
      return self._issue_session(db, user, ip=ip, ua=ua)
  ```
  Inject `challenge_store` into `AuthService.__init__` via `get_auth_service()` in `dependencies.py`.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_login_with_2fa_returns_challenge_no_cookies -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/services/auth_service.py backend/dependencies.py backend/tests/test_2fa_routes.py
  git commit -m "feat(auth): branch login flow on totp_enabled, issue challenge"
  ```

### Task 4.13: /auth/login/2fa success creates session

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_2fa_routes.py (append)
  def test_login_2fa_success_creates_session(client):
      _, secret = _enable_2fa(client, "kim@example.com", "correct horse battery 11")
      step1 = client.post("/auth/login", json={"email": "kim@example.com", "password": "correct horse battery 11"}).json()
      res = client.post(
          "/auth/login/2fa",
          json={"challenge_id": step1["challenge_id"], "code": pyotp.TOTP(secret).now()},
      )
      assert res.status_code == 200
      body = res.json()
      assert "access_token" in body and "refresh_token" in body
      assert body["user"]["email"] == "kim@example.com"
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_login_2fa_success_creates_session -v`
  Expected: FAIL with `404 Not Found`
- [ ] **Step 3: Implement**
  ```python
  # backend/services/auth_service.py (append)
  def login_2fa(self, db, challenge_id, code, *, ip, ua):
      user_id = self.challenges.consume(challenge_id)
      if not user_id:
          raise HTTPException(status_code=401, detail="Invalid or expired challenge")
      user = db.get(User, UUID(user_id))
      if not user or not user.totp_enabled or not user.totp_secret:
          raise HTTPException(status_code=401, detail="Invalid or expired challenge")
      secret = self.totp.decrypt(user.totp_secret)
      if not self.totp.verify(secret, code, valid_window=1):
          self._register_failed_login(db, user, ip=ip, ua=ua, reason="2fa_bad_code")
          self.audit.log(db, user_id=user.id, event="user.2fa_login_failed", ip=ip, user_agent=ua, metadata={})
          raise HTTPException(status_code=401, detail="Invalid code")
      return self._issue_session(db, user, ip=ip, ua=ua)
  ```
  ```python
  # backend/routers/auth.py (append)
  class Login2faBody(BaseModel):
      challenge_id: str
      code: str


  @router.post("/login/2fa")
  @limiter.limit("5/minute")
  def login_2fa(
      body: Login2faBody,
      request: Request,
      auth: AuthService = Depends(get_auth_service),
      db: Session = Depends(get_db),
  ) -> dict:
      return auth.login_2fa(
          db,
          body.challenge_id,
          body.code,
          ip=request.client.host if request.client else "",
          ua=request.headers.get("user-agent", ""),
      )
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py::test_login_2fa_success_creates_session -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/services/auth_service.py backend/routers/auth.py backend/tests/test_2fa_routes.py
  git commit -m "feat(auth): add POST /auth/login/2fa completion route"
  ```

### Task 4.14: Challenge single-use + expiry + wrong code increments fail count

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_2fa_routes.py (append)
  def test_login_2fa_challenge_single_use(client):
      _, secret = _enable_2fa(client, "leo@example.com", "correct horse battery 12")
      step1 = client.post("/auth/login", json={"email": "leo@example.com", "password": "correct horse battery 12"}).json()
      code = pyotp.TOTP(secret).now()
      first = client.post("/auth/login/2fa", json={"challenge_id": step1["challenge_id"], "code": code})
      second = client.post("/auth/login/2fa", json={"challenge_id": step1["challenge_id"], "code": code})
      assert first.status_code == 200
      assert second.status_code == 401


  def test_login_2fa_challenge_expires_after_5min(client, monkeypatch):
      _, secret = _enable_2fa(client, "max@example.com", "correct horse battery 13")
      step1 = client.post("/auth/login", json={"email": "max@example.com", "password": "correct horse battery 13"}).json()
      # fast-forward fakeredis clock by 301 seconds
      from dependencies import get_challenge_store
      store = get_challenge_store()
      store._client.set(f"auth:2fa:challenge:{step1['challenge_id']}", "nobody", ex=1)
      import time
      time.sleep(1.1)
      res = client.post("/auth/login/2fa", json={"challenge_id": step1["challenge_id"], "code": pyotp.TOTP(secret).now()})
      assert res.status_code == 401


  def test_login_2fa_wrong_code_increments_failed_count(client):
      _, secret = _enable_2fa(client, "nora@example.com", "correct horse battery 14")
      step1 = client.post("/auth/login", json={"email": "nora@example.com", "password": "correct horse battery 14"}).json()
      res = client.post("/auth/login/2fa", json={"challenge_id": step1["challenge_id"], "code": "000000"})
      assert res.status_code == 401
      assert res.json()["detail"] == "Invalid code"
      user = get_user(client, "nora@example.com")
      assert user.failed_login_count >= 1
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py -k "single_use or expires or increments" -v`
  Expected: PASS (covered by 4.13). If the expiry test fails because fakeredis does not honor EX in `time.sleep`, switch the test to assert by deleting the key directly.
- [ ] **Step 3: Implement**
  None.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_2fa_routes.py -v`
  Expected: PASS (all 2FA tests green)
- [ ] **Step 5: Commit**
  ```bash
  git add backend/tests/test_2fa_routes.py
  git commit -m "test(auth): cover 2fa challenge single-use, expiry, and failure counter"
  ```

### Task 4.15: Opus Gate 4A — 2FA security review

- [ ] **Step 1: Run the gate**
  ```
  Agent({
    subagent_type: "general-purpose",
    model: "opus",
    description: "Opus security review: 2FA flows",
    prompt: "Review backend/services/auth_service.py 2FA methods (start_2fa_setup, enable_2fa, disable_2fa, login, login_2fa), backend/routers/auth.py 2FA routes, and backend/services/challenge_store.py. Focus on: (1) Is `ChallengeStore.consume` truly atomic — can two parallel POST /auth/login/2fa both succeed? Confirm GETDEL is issued as a single command. (2) TOTP replay within the same 30-second window: does `disable_2fa` / `login_2fa` track the last-used counter so the same code cannot be reused? If not, flag it. (3) In `disable_2fa`, both checks must run and the error message must be identical for wrong-password and wrong-code — does any early return leak timing or message differences? (4) Setup → enable race: if a user calls /auth/2fa/setup twice in parallel, can one overwrite the other's secret in a way that breaks a subsequent /enable? (5) Does /auth/2fa/enable correctly revoke OTHER sessions only, keeping the setup session alive — and is the 'current session' identified by a constant-time compare of refresh_token_hash? Report findings as PASS / FAIL with file:line references."
  })
  ```
- [ ] **Step 2: Address findings**
  Open follow-up tasks for any FAIL items before proceeding to Phase 5.
- [ ] **Step 3: Commit fixes (if any)**
  ```bash
  git add backend/
  git commit -m "fix(auth): address Opus Gate 4A findings on 2FA flows"
  ```

---

## Phase 5: Sessions Dashboard + Admin

**Goal:** Users list and revoke their own sessions; admins read audit log, lock/unlock users, and force-disable 2FA.

**Files:**
- Create: `backend/routers/auth_admin.py`
- Create: `backend/tests/test_sessions_routes.py`
- Create: `backend/tests/test_admin_routes.py`
- Modify: `backend/routers/auth.py`
- Modify: `backend/services/audit_service.py`
- Modify: `backend/main.py`

### Task 5.1: GET /auth/sessions excludes revoked

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_sessions_routes.py
  from tests.helpers import register_and_login, auth_headers


  def test_sessions_list_excludes_revoked(client, db_session):
      tokens = register_and_login(client, "sess1@example.com", "correct horse battery 20")
      # second login -> second session
      second = client.post("/auth/login", json={"email": "sess1@example.com", "password": "correct horse battery 20"}).json()
      # revoke the second via logout
      client.post("/auth/logout", headers=auth_headers(second))
      res = client.get("/auth/sessions", headers=auth_headers(tokens))
      assert res.status_code == 200
      sessions = res.json()
      assert len(sessions) == 1
      assert all(s.get("revoked_at") is None for s in sessions)
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_sessions_routes.py::test_sessions_list_excludes_revoked -v`
  Expected: FAIL with `404 Not Found`
- [ ] **Step 3: Implement**
  ```python
  # backend/routers/auth.py (append)
  @router.get("/sessions")
  def list_sessions(
      request: Request,
      current_user: User = Depends(get_current_user),
      db: Session = Depends(get_db),
  ) -> list[dict]:
      import hmac
      current_hash = getattr(request.state, "session_hash", None)
      rows = (
          db.query(UserSession)
          .filter(
              UserSession.user_id == current_user.id,
              UserSession.revoked_at.is_(None),
              UserSession.expires_at > utcnow(),
          )
          .order_by(UserSession.last_used_at.desc())
          .all()
      )
      out = []
      for s in rows:
          is_current = bool(current_hash) and hmac.compare_digest(s.refresh_token_hash, current_hash)
          out.append({
              "id": str(s.id),
              "user_agent": s.user_agent,
              "ip_address": s.ip_address,
              "created_at": s.created_at.isoformat(),
              "last_used_at": s.last_used_at.isoformat(),
              "expires_at": s.expires_at.isoformat(),
              "is_current": is_current,
          })
      return out
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_sessions_routes.py::test_sessions_list_excludes_revoked -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/routers/auth.py backend/tests/test_sessions_routes.py
  git commit -m "feat(auth): add GET /auth/sessions listing active sessions"
  ```

### Task 5.2: List marks current session

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_sessions_routes.py (append)
  def test_sessions_list_marks_current_session(client):
      tokens = register_and_login(client, "sess2@example.com", "correct horse battery 21")
      client.post("/auth/login", json={"email": "sess2@example.com", "password": "correct horse battery 21"})
      res = client.get("/auth/sessions", headers=auth_headers(tokens))
      sessions = res.json()
      assert any(s["is_current"] for s in sessions)
      assert sum(1 for s in sessions if s["is_current"]) == 1
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_sessions_routes.py::test_sessions_list_marks_current_session -v`
  Expected: PASS if `request.state.session_hash` is populated; otherwise FAIL — fix by having the JWT middleware / `get_current_user` hydrate `request.state.session_hash` from the access token's `sid` claim.
- [ ] **Step 3: Implement**
  If the middleware does not yet carry `session_hash`, embed `sid` in the access token during `_issue_session` and decode it in `JWTAuthMiddleware`:
  ```python
  # backend/services/auth_service.py — inside _issue_session
  access = self.token.encode_access(user.id, extra={"sid": session_row.refresh_token_hash})
  ```
  ```python
  # backend/middleware/auth.py — after decoding JWT
  request.state.session_hash = payload.get("sid")
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_sessions_routes.py::test_sessions_list_marks_current_session -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/services/auth_service.py backend/middleware/auth.py backend/tests/test_sessions_routes.py
  git commit -m "feat(auth): thread session hash through JWT sid claim"
  ```

### Task 5.3: Sessions list scoped to user

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_sessions_routes.py (append)
  def test_sessions_list_scoped_to_user(client):
      a = register_and_login(client, "usera@example.com", "correct horse battery 22")
      b = register_and_login(client, "userb@example.com", "correct horse battery 23")
      res_a = client.get("/auth/sessions", headers=auth_headers(a)).json()
      res_b = client.get("/auth/sessions", headers=auth_headers(b)).json()
      assert len(res_a) == 1
      assert len(res_b) == 1
      assert res_a[0]["id"] != res_b[0]["id"]
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_sessions_routes.py::test_sessions_list_scoped_to_user -v`
  Expected: PASS (scoping is already enforced in the query).
- [ ] **Step 3: Implement**
  None.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_sessions_routes.py::test_sessions_list_scoped_to_user -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/tests/test_sessions_routes.py
  git commit -m "test(auth): verify sessions list scope"
  ```

### Task 5.4: Delete own session

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_sessions_routes.py (append)
  def test_sessions_delete_own_session(client):
      a = register_and_login(client, "del1@example.com", "correct horse battery 24")
      b = client.post("/auth/login", json={"email": "del1@example.com", "password": "correct horse battery 24"}).json()
      sessions = client.get("/auth/sessions", headers=auth_headers(a)).json()
      other = next(s for s in sessions if not s["is_current"])
      res = client.delete(f"/auth/sessions/{other['id']}", headers=auth_headers(a))
      assert res.status_code == 200
      # b's refresh must no longer work
      assert client.post("/auth/refresh", json={"refresh_token": b["refresh_token"]}).status_code == 401
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_sessions_routes.py::test_sessions_delete_own_session -v`
  Expected: FAIL with `404 Not Found`
- [ ] **Step 3: Implement**
  ```python
  # backend/routers/auth.py (append)
  @router.delete("/sessions/{session_id}")
  def delete_session(
      session_id: UUID,
      request: Request,
      current_user: User = Depends(get_current_user),
      db: Session = Depends(get_db),
  ) -> dict:
      current_hash = getattr(request.state, "session_hash", None)
      result = db.execute(
          text(
              "UPDATE user_sessions SET revoked_at = :now "
              "WHERE id = :sid AND user_id = :uid AND revoked_at IS NULL "
              "RETURNING id, refresh_token_hash"
          ),
          {"now": utcnow(), "sid": str(session_id), "uid": str(current_user.id)},
      ).first()
      if result is None:
          raise HTTPException(status_code=404, detail="Not found")
      db.commit()
      current_revoked = bool(current_hash) and hmac.compare_digest(result.refresh_token_hash, current_hash)
      return {"status": "ok", "current_session_revoked": current_revoked}
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_sessions_routes.py::test_sessions_delete_own_session -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/routers/auth.py backend/tests/test_sessions_routes.py
  git commit -m "feat(auth): add DELETE /auth/sessions/{id} with DB-level ownership"
  ```

### Task 5.5: Deleting other user's session returns 404 (not 403)

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_sessions_routes.py (append)
  def test_sessions_delete_other_users_session_404(client):
      a = register_and_login(client, "own1@example.com", "correct horse battery 25")
      b = register_and_login(client, "own2@example.com", "correct horse battery 26")
      b_sessions = client.get("/auth/sessions", headers=auth_headers(b)).json()
      b_id = b_sessions[0]["id"]
      res = client.delete(f"/auth/sessions/{b_id}", headers=auth_headers(a))
      assert res.status_code == 404


  def test_sessions_delete_nonexistent_session_404(client):
      a = register_and_login(client, "ghost@example.com", "correct horse battery 27")
      res = client.delete("/auth/sessions/00000000-0000-0000-0000-000000000000", headers=auth_headers(a))
      assert res.status_code == 404
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_sessions_routes.py -k "other_users or nonexistent" -v`
  Expected: PASS (covered by 5.4 ownership-in-SQL approach)
- [ ] **Step 3: Implement**
  None.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_sessions_routes.py -k "other_users or nonexistent" -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/tests/test_sessions_routes.py
  git commit -m "test(auth): verify session deletion does not leak existence"
  ```

### Task 5.6: Revoking current session flags response

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_sessions_routes.py (append)
  def test_sessions_delete_current_session_flag_in_response(client):
      a = register_and_login(client, "self@example.com", "correct horse battery 28")
      sessions = client.get("/auth/sessions", headers=auth_headers(a)).json()
      current = next(s for s in sessions if s["is_current"])
      res = client.delete(f"/auth/sessions/{current['id']}", headers=auth_headers(a))
      assert res.status_code == 200
      assert res.json()["current_session_revoked"] is True
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_sessions_routes.py::test_sessions_delete_current_session_flag_in_response -v`
  Expected: PASS (covered by 5.4)
- [ ] **Step 3: Implement**
  None.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_sessions_routes.py::test_sessions_delete_current_session_flag_in_response -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/tests/test_sessions_routes.py
  git commit -m "test(auth): verify current session revoke flag"
  ```

### Task 5.7: Audit query helper

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_admin_routes.py
  from tests.helpers import register_and_login, make_admin, auth_headers


  def test_admin_audit_requires_admin_role(client):
      tokens = register_and_login(client, "reg@example.com", "correct horse battery 29")
      res = client.get("/admin/audit", headers=auth_headers(tokens))
      assert res.status_code == 403
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_admin_routes.py::test_admin_audit_requires_admin_role -v`
  Expected: FAIL with `404 Not Found`
- [ ] **Step 3: Implement**
  ```python
  # backend/services/audit_service.py (append)
  def query(
      self,
      db: Session,
      *,
      event: str | None = None,
      user_id: UUID | None = None,
      limit: int = 50,
      offset: int = 0,
  ) -> list[AuditLog]:
      limit = max(1, min(200, limit))
      q = db.query(AuditLog)
      if event:
          q = q.filter(AuditLog.event == event)
      if user_id:
          q = q.filter(AuditLog.user_id == user_id)
      return q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
  ```
  ```python
  # backend/routers/auth_admin.py
  from uuid import UUID

  from fastapi import APIRouter, Depends, HTTPException
  from pydantic import BaseModel
  from sqlmodel import Session

  from database import get_db
  from dependencies import get_admin_user, get_audit_service, get_auth_service
  from models.auth import User, UserSession
  from services.audit_service import AuditService
  from services.auth_service import AuthService
  from utils.time import utcnow

  router = APIRouter(prefix="/admin", tags=["admin"])


  @router.get("/audit")
  def list_audit(
      event: str | None = None,
      user_id: UUID | None = None,
      limit: int = 50,
      offset: int = 0,
      _: User = Depends(get_admin_user),
      audit: AuditService = Depends(get_audit_service),
      db: Session = Depends(get_db),
  ) -> list[dict]:
      rows = audit.query(db, event=event, user_id=user_id, limit=limit, offset=offset)
      return [
          {
              "id": str(r.id),
              "user_id": str(r.user_id) if r.user_id else None,
              "event": r.event,
              "ip_address": r.ip_address,
              "user_agent": r.user_agent,
              "metadata_json": r.metadata_json,
              "created_at": r.created_at.isoformat(),
          }
          for r in rows
      ]
  ```
  ```python
  # backend/main.py (modify)
  from routers import auth_admin
  app.include_router(auth_admin.router)
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_admin_routes.py::test_admin_audit_requires_admin_role -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/routers/auth_admin.py backend/services/audit_service.py backend/main.py backend/tests/test_admin_routes.py
  git commit -m "feat(admin): add GET /admin/audit with admin guard"
  ```

### Task 5.8: Audit filter by event + user_id + pagination

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_admin_routes.py (append)
  def test_admin_audit_filter_by_event(client):
      admin = make_admin(client, "admin1@example.com", "correct horse battery 30")
      register_and_login(client, "target1@example.com", "correct horse battery 31")
      res = client.get("/admin/audit?event=user.register", headers=auth_headers(admin))
      assert res.status_code == 200
      events = {r["event"] for r in res.json()}
      assert events == {"user.register"}


  def test_admin_audit_filter_by_user_id(client):
      admin = make_admin(client, "admin2@example.com", "correct horse battery 32")
      a = register_and_login(client, "aa@example.com", "correct horse battery 33")
      register_and_login(client, "bb@example.com", "correct horse battery 34")
      uid = client.get("/auth/me", headers=auth_headers(a)).json()["id"]
      res = client.get(f"/admin/audit?user_id={uid}", headers=auth_headers(admin))
      assert all(r["user_id"] == uid for r in res.json())


  def test_admin_audit_pagination(client):
      admin = make_admin(client, "admin3@example.com", "correct horse battery 35")
      for i in range(5):
          register_and_login(client, f"pg{i}@example.com", f"correct horse battery {40 + i}")
      first = client.get("/admin/audit?limit=2&offset=0", headers=auth_headers(admin)).json()
      second = client.get("/admin/audit?limit=2&offset=2", headers=auth_headers(admin)).json()
      assert len(first) == 2 and len(second) == 2
      assert {r["id"] for r in first}.isdisjoint({r["id"] for r in second})
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_admin_routes.py -k "filter_by or pagination" -v`
  Expected: PASS (implementation from 5.7 covers it)
- [ ] **Step 3: Implement**
  None.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_admin_routes.py -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/tests/test_admin_routes.py
  git commit -m "test(admin): cover audit filtering and pagination"
  ```

### Task 5.9: Admin lock/unlock user

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_admin_routes.py (append)
  def test_admin_lock_user_sets_locked_until(client):
      admin = make_admin(client, "admin4@example.com", "correct horse battery 45")
      target = register_and_login(client, "target2@example.com", "correct horse battery 46")
      uid = client.get("/auth/me", headers=auth_headers(target)).json()["id"]
      res = client.post(f"/admin/users/{uid}/lock", json={"duration_minutes": 30}, headers=auth_headers(admin))
      assert res.status_code == 200
      login = client.post("/auth/login", json={"email": "target2@example.com", "password": "correct horse battery 46"})
      assert login.status_code == 423


  def test_admin_unlock_user_clears_lock_and_counter(client):
      admin = make_admin(client, "admin5@example.com", "correct horse battery 47")
      target = register_and_login(client, "target3@example.com", "correct horse battery 48")
      uid = client.get("/auth/me", headers=auth_headers(target)).json()["id"]
      client.post(f"/admin/users/{uid}/lock", json={"duration_minutes": 30}, headers=auth_headers(admin))
      res = client.post(f"/admin/users/{uid}/unlock", headers=auth_headers(admin))
      assert res.status_code == 200
      login = client.post("/auth/login", json={"email": "target3@example.com", "password": "correct horse battery 48"})
      assert login.status_code == 200
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_admin_routes.py -k "lock_user or unlock_user" -v`
  Expected: FAIL with `404 Not Found`
- [ ] **Step 3: Implement**
  ```python
  # backend/routers/auth_admin.py (append)
  from datetime import timedelta


  class LockBody(BaseModel):
      duration_minutes: int


  @router.post("/users/{user_id}/lock")
  def lock_user(
      user_id: UUID,
      body: LockBody,
      admin: User = Depends(get_admin_user),
      db: Session = Depends(get_db),
      audit: AuditService = Depends(get_audit_service),
  ) -> dict:
      user = db.get(User, user_id)
      if not user:
          raise HTTPException(status_code=404)
      user.locked_until = utcnow() + timedelta(minutes=body.duration_minutes)
      db.add(user)
      db.commit()
      audit.log(db, user_id=admin.id, event="admin.user_locked", ip=None, user_agent=None, metadata={"target_user_id": str(user_id)})
      return {"status": "ok"}


  @router.post("/users/{user_id}/unlock")
  def unlock_user(
      user_id: UUID,
      admin: User = Depends(get_admin_user),
      db: Session = Depends(get_db),
      audit: AuditService = Depends(get_audit_service),
  ) -> dict:
      user = db.get(User, user_id)
      if not user:
          raise HTTPException(status_code=404)
      user.locked_until = None
      user.failed_login_count = 0
      db.add(user)
      db.commit()
      audit.log(db, user_id=admin.id, event="admin.user_unlocked", ip=None, user_agent=None, metadata={"target_user_id": str(user_id)})
      return {"status": "ok"}
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_admin_routes.py -k "lock_user or unlock_user" -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/routers/auth_admin.py backend/tests/test_admin_routes.py
  git commit -m "feat(admin): add lock/unlock user endpoints"
  ```

### Task 5.10: Admin disable 2FA

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_admin_routes.py (append)
  import pyotp


  def test_admin_disable_2fa_flips_flag_and_revokes_sessions(client):
      admin = make_admin(client, "admin6@example.com", "correct horse battery 50")
      target = register_and_login(client, "target4@example.com", "correct horse battery 51")
      setup = client.post("/auth/2fa/setup", headers=auth_headers(target)).json()
      client.post("/auth/2fa/enable", json={"code": pyotp.TOTP(setup["secret"]).now()}, headers=auth_headers(target))
      uid = client.get("/auth/me", headers=auth_headers(target)).json()["id"]
      res = client.post(f"/admin/users/{uid}/disable-2fa", headers=auth_headers(admin))
      assert res.status_code == 200
      assert client.post("/auth/refresh", json={"refresh_token": target["refresh_token"]}).status_code == 401


  def test_admin_endpoints_reject_regular_user(client):
      reg = register_and_login(client, "plain@example.com", "correct horse battery 52")
      assert client.post("/admin/users/00000000-0000-0000-0000-000000000000/lock", json={"duration_minutes": 10}, headers=auth_headers(reg)).status_code == 403
      assert client.post("/admin/users/00000000-0000-0000-0000-000000000000/unlock", headers=auth_headers(reg)).status_code == 403
      assert client.post("/admin/users/00000000-0000-0000-0000-000000000000/disable-2fa", headers=auth_headers(reg)).status_code == 403
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_admin_routes.py -k "disable_2fa or reject_regular" -v`
  Expected: FAIL with `404 Not Found` for the disable route
- [ ] **Step 3: Implement**
  ```python
  # backend/routers/auth_admin.py (append)
  @router.post("/users/{user_id}/disable-2fa")
  def admin_disable_2fa(
      user_id: UUID,
      admin: User = Depends(get_admin_user),
      db: Session = Depends(get_db),
      audit: AuditService = Depends(get_audit_service),
  ) -> dict:
      user = db.get(User, user_id)
      if not user:
          raise HTTPException(status_code=404)
      user.totp_secret = None
      user.totp_enabled = False
      db.add(user)
      for s in db.query(UserSession).filter(
          UserSession.user_id == user.id,
          UserSession.revoked_at.is_(None),
      ).all():
          s.revoked_at = utcnow()
          db.add(s)
      db.commit()
      audit.log(
          db,
          user_id=admin.id,
          event="admin.2fa_disabled_by_admin",
          ip=None,
          user_agent=None,
          metadata={"admin_id": str(admin.id), "target_user_id": str(user_id)},
      )
      return {"status": "ok"}
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_admin_routes.py -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/routers/auth_admin.py backend/tests/test_admin_routes.py
  git commit -m "feat(admin): add force-disable 2FA endpoint"
  ```

---

## Phase 6: Secure Existing Routes + reports.user_id Migration

**Goal:** Attach `user_id` to reports, scope every existing router by the current user, and run the destructive 0003 migration.

**Files:**
- Create: `backend/alembic/versions/0003_reports_user_id.py`
- Create: `backend/tests/test_migration_0003.py`
- Create: `backend/tests/test_reports_ownership.py`
- Modify: `backend/models/report.py`
- Modify: `backend/routers/reports.py`, `sessions.py`, `analysis.py`, `therapy_plans.py`, `suggestions.py`, `exports.py`, `soap.py`, `legacy.py`
- Modify: `backend/services/auth_service.py` (if session creation threads user_id)

### Task 6.1: Migration 0003 drops existing reports

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_migration_0003.py
  import pytest
  from alembic import command
  from alembic.config import Config
  from sqlalchemy import create_engine, inspect, text


  @pytest.fixture
  def alembic_cfg(tmp_path):
      cfg = Config("backend/alembic.ini")
      db_url = f"sqlite:///{tmp_path}/mig.db"
      cfg.set_main_option("sqlalchemy.url", db_url)
      return cfg, db_url


  def test_migration_0003_drops_existing_reports(alembic_cfg):
      cfg, db_url = alembic_cfg
      command.upgrade(cfg, "0002")
      eng = create_engine(db_url)
      with eng.begin() as conn:
          conn.execute(text("INSERT INTO reports (id, content) VALUES ('r1', 'x')"))
      command.upgrade(cfg, "0003")
      with eng.begin() as conn:
          rows = conn.execute(text("SELECT COUNT(*) FROM reports")).scalar()
      assert rows == 0
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_migration_0003.py::test_migration_0003_drops_existing_reports -v`
  Expected: FAIL — revision 0003 does not exist
- [ ] **Step 3: Implement**
  ```python
  # backend/alembic/versions/0003_reports_user_id.py
  """reports.user_id (destructive)

  Revision ID: 0003
  Revises: 0002
  Create Date: 2026-04-13
  """
  from __future__ import annotations

  import sqlalchemy as sa
  from alembic import op
  from sqlalchemy.dialects.postgresql import UUID

  revision = "0003"
  down_revision = "0002"
  branch_labels = None
  depends_on = None


  def upgrade() -> None:
      op.execute("DELETE FROM reports")
      op.add_column("reports", sa.Column("user_id", UUID(as_uuid=True), nullable=False))
      op.create_foreign_key(
          "fk_reports_user",
          "reports",
          "users",
          ["user_id"],
          ["id"],
          ondelete="CASCADE",
      )
      op.create_index("ix_reports_user_id", "reports", ["user_id"])


  def downgrade() -> None:
      op.drop_index("ix_reports_user_id", table_name="reports")
      op.drop_constraint("fk_reports_user", "reports", type_="foreignkey")
      op.drop_column("reports", "user_id")
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_migration_0003.py::test_migration_0003_drops_existing_reports -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/alembic/versions/0003_reports_user_id.py backend/tests/test_migration_0003.py
  git commit -m "feat(db): add migration 0003 reports.user_id (destructive)"
  ```

### Task 6.2: Migration adds NOT NULL column + downgrade drops it

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_migration_0003.py (append)
  def test_migration_0003_adds_user_id_not_null(alembic_cfg):
      cfg, db_url = alembic_cfg
      command.upgrade(cfg, "0003")
      eng = create_engine(db_url)
      cols = {c["name"]: c for c in inspect(eng).get_columns("reports")}
      assert "user_id" in cols
      assert cols["user_id"]["nullable"] is False


  def test_migration_0003_downgrade_drops_column(alembic_cfg):
      cfg, db_url = alembic_cfg
      command.upgrade(cfg, "0003")
      command.downgrade(cfg, "0002")
      eng = create_engine(db_url)
      cols = {c["name"] for c in inspect(eng).get_columns("reports")}
      assert "user_id" not in cols
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_migration_0003.py -v`
  Expected: PASS (already covered)
- [ ] **Step 3: Implement**
  None.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_migration_0003.py -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/tests/test_migration_0003.py
  git commit -m "test(db): verify 0003 upgrade/downgrade column shape"
  ```

### Task 6.3: Report model gets user_id

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_reports_ownership.py
  from uuid import uuid4

  from models.report import Report


  def test_report_model_has_user_id_field():
      assert "user_id" in Report.model_fields
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_reports_ownership.py::test_report_model_has_user_id_field -v`
  Expected: FAIL with `AssertionError` (field missing)
- [ ] **Step 3: Implement**
  ```python
  # backend/models/report.py (modify)
  from uuid import UUID
  from sqlmodel import Field

  class Report(SQLModel, table=True):
      # ... existing fields ...
      user_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_reports_ownership.py::test_report_model_has_user_id_field -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/models/report.py backend/tests/test_reports_ownership.py
  git commit -m "feat(reports): add user_id field to Report model"
  ```

### Task 6.4: /reports list scoped to current user

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_reports_ownership.py (append)
  from tests.helpers import register_and_login, auth_headers, seed_report


  def test_reports_list_scoped_to_current_user(client, db_session):
      a = register_and_login(client, "rep_a@example.com", "correct horse battery 60")
      b = register_and_login(client, "rep_b@example.com", "correct horse battery 61")
      uid_a = client.get("/auth/me", headers=auth_headers(a)).json()["id"]
      uid_b = client.get("/auth/me", headers=auth_headers(b)).json()["id"]
      seed_report(db_session, user_id=uid_a, title="A-1")
      seed_report(db_session, user_id=uid_b, title="B-1")
      res = client.get("/reports", headers=auth_headers(a))
      titles = [r["title"] for r in res.json()["items"]]
      assert titles == ["A-1"]
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_reports_ownership.py::test_reports_list_scoped_to_current_user -v`
  Expected: FAIL — current `/reports` returns both rows
- [ ] **Step 3: Implement**
  ```python
  # backend/routers/reports.py (modify GET /reports)
  from dependencies import get_current_user
  from models.auth import User

  @router.get("/reports")
  def list_reports(
      limit: int = 50,
      offset: int = 0,
      current_user: User = Depends(get_current_user),
      db: Session = Depends(get_db),
  ):
      q = (
          db.query(Report)
          .filter(Report.user_id == current_user.id)
          .order_by(Report.created_at.desc())
          .offset(offset)
          .limit(limit)
      )
      return {"items": [r.model_dump() for r in q.all()]}
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_reports_ownership.py::test_reports_list_scoped_to_current_user -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/routers/reports.py backend/tests/test_reports_ownership.py
  git commit -m "feat(reports): scope GET /reports to current user"
  ```

### Task 6.5: GET /reports/{id} returns 404 for other user

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_reports_ownership.py (append)
  def test_reports_get_other_user_returns_404(client, db_session):
      a = register_and_login(client, "rep_c@example.com", "correct horse battery 62")
      b = register_and_login(client, "rep_d@example.com", "correct horse battery 63")
      uid_b = client.get("/auth/me", headers=auth_headers(b)).json()["id"]
      rid = seed_report(db_session, user_id=uid_b, title="Secret")
      res = client.get(f"/reports/{rid}", headers=auth_headers(a))
      assert res.status_code == 404
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_reports_ownership.py::test_reports_get_other_user_returns_404 -v`
  Expected: FAIL — returns 200 with B's report
- [ ] **Step 3: Implement**
  ```python
  # backend/routers/reports.py (modify GET /reports/{id})
  @router.get("/reports/{report_id}")
  def get_report(
      report_id: UUID,
      current_user: User = Depends(get_current_user),
      db: Session = Depends(get_db),
  ):
      row = db.query(Report).filter(
          Report.id == report_id,
          Report.user_id == current_user.id,
      ).first()
      if row is None:
          raise HTTPException(status_code=404, detail="Not found")
      return row.model_dump()
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_reports_ownership.py::test_reports_get_other_user_returns_404 -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/routers/reports.py backend/tests/test_reports_ownership.py
  git commit -m "feat(reports): enforce ownership on GET /reports/{id}"
  ```

### Task 6.6: PDF export ownership enforced

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_reports_ownership.py (append)
  def test_reports_pdf_export_ownership_enforced(client, db_session):
      a = register_and_login(client, "rep_e@example.com", "correct horse battery 64")
      b = register_and_login(client, "rep_f@example.com", "correct horse battery 65")
      uid_b = client.get("/auth/me", headers=auth_headers(b)).json()["id"]
      rid = seed_report(db_session, user_id=uid_b, title="B-report")
      res = client.get(f"/reports/{rid}/pdf", headers=auth_headers(a))
      assert res.status_code == 404
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_reports_ownership.py::test_reports_pdf_export_ownership_enforced -v`
  Expected: FAIL — `exports.py` has no auth
- [ ] **Step 3: Implement**
  ```python
  # backend/routers/exports.py (modify)
  @router.get("/reports/{report_id}/pdf")
  def export_pdf(
      report_id: UUID,
      current_user: User = Depends(get_current_user),
      db: Session = Depends(get_db),
  ):
      row = db.query(Report).filter(
          Report.id == report_id,
          Report.user_id == current_user.id,
      ).first()
      if row is None:
          raise HTTPException(status_code=404, detail="Not found")
      return StreamingResponse(render_pdf(row), media_type="application/pdf")
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_reports_ownership.py::test_reports_pdf_export_ownership_enforced -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/routers/exports.py backend/tests/test_reports_ownership.py
  git commit -m "feat(exports): enforce report ownership on PDF export"
  ```

### Task 6.7: Sessions router ownership

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_reports_ownership.py (append)
  def test_sessions_get_other_user_returns_404(client):
      a = register_and_login(client, "s_a@example.com", "correct horse battery 66")
      b = register_and_login(client, "s_b@example.com", "correct horse battery 67")
      sid = client.post("/sessions", json={}, headers=auth_headers(b)).json()["id"]
      res = client.get(f"/sessions/{sid}", headers=auth_headers(a))
      assert res.status_code == 404


  def test_sessions_generate_writes_user_id(client, db_session):
      a = register_and_login(client, "s_gen@example.com", "correct horse battery 68")
      uid = client.get("/auth/me", headers=auth_headers(a)).json()["id"]
      sid = client.post("/sessions", json={}, headers=auth_headers(a)).json()["id"]
      rep = client.post(f"/sessions/{sid}/generate", json={"report_type": "befundbericht"}, headers=auth_headers(a)).json()
      from models.report import Report
      row = db_session.get(Report, rep["id"])
      assert str(row.user_id) == uid
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_reports_ownership.py -k "sessions_get_other or generate_writes_user_id" -v`
  Expected: FAIL — sessions have no auth and generate does not thread user_id
- [ ] **Step 3: Implement**
  ```python
  # backend/routers/sessions.py (modify)
  @router.post("/sessions")
  def create_session(
      body: CreateSessionBody,
      current_user: User = Depends(get_current_user),
      store: SessionStore = Depends(get_session_store),
  ):
      session_state = store.create(owner_user_id=str(current_user.id))
      return session_state.public_dict()


  @router.get("/sessions/{session_id}")
  def get_session(
      session_id: str,
      current_user: User = Depends(get_current_user),
      store: SessionStore = Depends(get_session_store),
  ):
      s = store.get(session_id)
      if s is None or s.user_id != str(current_user.id):
          raise HTTPException(status_code=404, detail="Not found")
      return s.public_dict()


  @router.post("/sessions/{session_id}/generate")
  def generate_report(
      session_id: str,
      body: GenerateBody,
      current_user: User = Depends(get_current_user),
      store: SessionStore = Depends(get_session_store),
      db: Session = Depends(get_db),
  ):
      s = store.get(session_id)
      if s is None or s.user_id != str(current_user.id):
          raise HTTPException(status_code=404, detail="Not found")
      report = build_report(s, body.report_type)
      report.user_id = current_user.id
      db.add(report)
      db.commit()
      return report.model_dump()
  ```
  And extend `SessionState` (`backend/services/session_store.py`) with a `user_id: str | None` field threaded through `create()`.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_reports_ownership.py -k "sessions_get_other or generate_writes_user_id" -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/routers/sessions.py backend/services/session_store.py backend/tests/test_reports_ownership.py
  git commit -m "feat(sessions): scope sessions by user and stamp reports on generate"
  ```

### Task 6.8: SOAP ownership

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_reports_ownership.py (append)
  def test_soap_ownership_enforced(client, db_session):
      a = register_and_login(client, "soap_a@example.com", "correct horse battery 70")
      b = register_and_login(client, "soap_b@example.com", "correct horse battery 71")
      uid_b = client.get("/auth/me", headers=auth_headers(b)).json()["id"]
      rid = seed_report(db_session, user_id=uid_b, title="Soap B")
      assert client.get(f"/reports/{rid}/soap", headers=auth_headers(a)).status_code == 404
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_reports_ownership.py::test_soap_ownership_enforced -v`
  Expected: FAIL
- [ ] **Step 3: Implement**
  ```python
  # backend/routers/soap.py (modify both routes)
  @router.post("/sessions/{session_id}/soap")
  def create_soap(
      session_id: str,
      current_user: User = Depends(get_current_user),
      store: SessionStore = Depends(get_session_store),
      db: Session = Depends(get_db),
  ):
      s = store.get(session_id)
      if s is None or s.user_id != str(current_user.id):
          raise HTTPException(status_code=404)
      # ... existing logic ...


  @router.get("/reports/{report_id}/soap")
  def get_soap(
      report_id: UUID,
      current_user: User = Depends(get_current_user),
      db: Session = Depends(get_db),
  ):
      row = db.query(Report).filter(
          Report.id == report_id,
          Report.user_id == current_user.id,
      ).first()
      if row is None:
          raise HTTPException(status_code=404)
      return {"soap": row.soap_notes}
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_reports_ownership.py::test_soap_ownership_enforced -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/routers/soap.py backend/tests/test_reports_ownership.py
  git commit -m "feat(soap): enforce ownership on both SOAP routes"
  ```

### Task 6.9: /analysis/compare rejects cross-user reports

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_reports_ownership.py (append)
  def test_analysis_compare_rejects_other_users_report(client, db_session):
      a = register_and_login(client, "cmp_a@example.com", "correct horse battery 72")
      b = register_and_login(client, "cmp_b@example.com", "correct horse battery 73")
      uid_a = client.get("/auth/me", headers=auth_headers(a)).json()["id"]
      uid_b = client.get("/auth/me", headers=auth_headers(b)).json()["id"]
      ra = seed_report(db_session, user_id=uid_a, title="A")
      rb = seed_report(db_session, user_id=uid_b, title="B")
      res = client.post("/analysis/compare", json={"report_ids": [ra, rb]}, headers=auth_headers(a))
      assert res.status_code == 404
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_reports_ownership.py::test_analysis_compare_rejects_other_users_report -v`
  Expected: FAIL
- [ ] **Step 3: Implement**
  ```python
  # backend/routers/analysis.py (modify compare)
  @router.post("/analysis/compare")
  def compare(
      body: CompareBody,
      current_user: User = Depends(get_current_user),
      db: Session = Depends(get_db),
  ):
      rows = db.query(Report).filter(
          Report.id.in_(body.report_ids),
          Report.user_id == current_user.id,
      ).all()
      if len(rows) != len(body.report_ids):
          raise HTTPException(status_code=404, detail="Not found")
      return run_compare(rows)
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_reports_ownership.py::test_analysis_compare_rejects_other_users_report -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/routers/analysis.py backend/tests/test_reports_ownership.py
  git commit -m "feat(analysis): reject compare when any report is not owned"
  ```

### Task 6.10: therapy_plans, suggestions, legacy require auth

- [ ] **Step 1: Write the failing test**
  ```python
  # backend/tests/test_reports_ownership.py (append)
  def test_therapy_plan_requires_auth(client):
      res = client.post("/sessions/abc123/therapy-plan", json={})
      assert res.status_code == 401


  def test_legacy_process_audio_requires_auth(client):
      res = client.post("/process-audio", files={"file": ("a.wav", b"x", "audio/wav")})
      assert res.status_code == 401
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_reports_ownership.py -k "requires_auth" -v`
  Expected: FAIL — routes currently anonymous
- [ ] **Step 3: Implement**
  Add `current_user: User = Depends(get_current_user)` to every route in `backend/routers/therapy_plans.py`, `suggestions.py`, `legacy.py`, `analysis.py` (the phonological endpoints), and any remaining unauthenticated handler. For handlers that accept a `session_id`, also verify ownership via `store.get()`.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_reports_ownership.py -k "requires_auth" -v`
  Expected: PASS
- [ ] **Step 5: Commit**
  ```bash
  git add backend/routers/therapy_plans.py backend/routers/suggestions.py backend/routers/legacy.py backend/routers/analysis.py backend/tests/test_reports_ownership.py
  git commit -m "feat(auth): require auth on therapy-plan, suggestions, legacy, analysis"
  ```

### Task 6.11: Full regression run

- [ ] **Step 1: Write the failing test**
  No new test — run the full suite.
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest -q`
  Expected: Any regression surfaces here.
- [ ] **Step 3: Implement**
  Fix any red test by updating the corresponding router/service. Most likely fix: existing tests that call routes without auth need a `client` fixture upgrade that auto-injects a test user, or the tests need explicit `auth_headers(...)` calls.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest -q`
  Expected: PASS (all previous tests + new ownership tests)
- [ ] **Step 5: Commit**
  ```bash
  git add backend/tests/
  git commit -m "test(auth): update legacy tests to authenticate against secured routes"
  ```

### Task 6.12: Opus Gate 6A — IDOR sweep

- [ ] **Step 1: Run the gate**
  ```
  Agent({
    subagent_type: "general-purpose",
    model: "opus",
    description: "Opus security review: IDOR sweep",
    prompt: "Run an IDOR audit on backend/routers/reports.py, sessions.py, analysis.py, therapy_plans.py, suggestions.py, exports.py, soap.py, legacy.py, health.py. Execute `rg -n 'from_id|get.*report|get.*session|query\\(.*Report|query\\(.*Session' backend/routers/` and for each hit confirm: (1) Every SELECT, UPDATE, DELETE that touches reports or user_sessions includes `user_id = current_user.id` DIRECTLY in the SQL / query builder — not checked after fetch. (2) No route uses `db.get(Report, id)` followed by a post-hoc `if row.user_id != current_user.id` check — it must be `db.query(Report).filter(Report.id==id, Report.user_id==current_user.id).first()`. (3) Every router has `Depends(get_current_user)` on every route (no mixed anonymous handlers). (4) For routes that accept session_id (a 12-char hex string, not a DB row), ownership is verified via `store.get(sid).user_id == str(current_user.id)`. (5) /analysis/compare refuses to proceed if ANY of the report_ids is not owned. Report findings as PASS / FAIL with file:line references and a suggested fix for each FAIL."
  })
  ```
- [ ] **Step 2: Address findings**
  Create TDD follow-up tasks for each FAIL with a new test first.
- [ ] **Step 3: Commit fixes (if any)**
  ```bash
  git add backend/
  git commit -m "fix(auth): address Opus Gate 6A IDOR findings"
  ```
## Phase 7: Frontend AuthProvider + Edge Middleware + Proxy

**Goal:** Client-side auth plumbing — context, edge middleware, Route Handler cookie proxy, and single-flight 401 refresh in the API client.

**Files:**
- Create: `frontend/src/features/auth/types.ts`
- Create: `frontend/src/features/auth/api.ts`
- Create: `frontend/src/features/auth/api.test.ts`
- Create: `frontend/src/features/auth/hooks/useAuth.ts`
- Create: `frontend/src/providers/AuthProvider.tsx`
- Create: `frontend/src/providers/AuthProvider.test.tsx`
- Create: `frontend/src/middleware.ts`
- Create: `frontend/src/middleware.test.ts`
- Create: `frontend/src/app/api/auth/login/route.ts`
- Create: `frontend/src/app/api/auth/login/route.test.ts`
- Create: `frontend/src/app/api/auth/login/2fa/route.ts`
- Create: `frontend/src/app/api/auth/logout/route.ts`
- Create: `frontend/src/app/api/auth/logout/route.test.ts`
- Create: `frontend/src/app/api/auth/refresh/route.ts`
- Create: `frontend/src/app/api/auth/refresh/route.test.ts`
- Create: `frontend/src/app/api/auth/register/route.ts`
- Create: `frontend/src/app/api/auth/me/route.ts`
- Create: `frontend/src/app/api/auth/[...rest]/route.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/next.config.ts`

### Task 7.1: Auth types module

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/features/auth/types.test.ts`:
  ```ts
  import { describe, it, expect } from "vitest";
  import type { User, AuthState } from "./types";

  describe("auth types", () => {
    it("User has id, email, role, totp_enabled, created_at", () => {
      const u: User = {
        id: "u1",
        email: "x@y.z",
        role: "user",
        totp_enabled: false,
        created_at: "2026-04-13T00:00:00Z",
      };
      expect(u.role).toBe("user");
    });

    it("AuthState supports loading | authenticated | unauthenticated", () => {
      const a: AuthState = { status: "loading" };
      const b: AuthState = {
        status: "authenticated",
        user: {
          id: "u1",
          email: "x@y.z",
          role: "admin",
          totp_enabled: true,
          created_at: "",
        },
      };
      const c: AuthState = { status: "unauthenticated" };
      expect([a.status, b.status, c.status]).toEqual([
        "loading",
        "authenticated",
        "unauthenticated",
      ]);
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/features/auth/types.test.ts`
  Expected: FAIL with `Cannot find module './types'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/features/auth/types.ts`:
  ```ts
  export type UserRole = "user" | "admin";

  export interface User {
    id: string;
    email: string;
    role: UserRole;
    totp_enabled: boolean;
    created_at: string;
  }

  export type AuthState =
    | { status: "loading" }
    | { status: "authenticated"; user: User }
    | { status: "unauthenticated" };

  export interface LoginSuccess {
    access_token: string;
    refresh_token: string;
    user: User;
  }

  export interface LoginTwoFactorRequired {
    step: "2fa_required";
    challenge_id: string;
  }

  export type LoginResponse = LoginSuccess | LoginTwoFactorRequired;
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/features/auth/types.test.ts`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/features/auth/types.ts frontend/src/features/auth/types.test.ts
  git commit -m "feat(auth-ui): add auth types module"
  ```

### Task 7.2: Auth API client wrapper

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/features/auth/api.test.ts`:
  ```ts
  import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
  import { authApi } from "./api";

  describe("authApi", () => {
    beforeEach(() => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify({ ok: true }), { status: 200 }),
      );
    });
    afterEach(() => {
      vi.restoreAllMocks();
    });

    it("login POSTs to /api/auth/login with credentials include", async () => {
      await authApi.login("a@b.c", "pw123456789012");
      const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock
        .calls[0];
      expect(call[0]).toBe("/api/auth/login");
      expect(call[1].method).toBe("POST");
      expect(call[1].credentials).toBe("include");
      expect(JSON.parse(call[1].body)).toEqual({
        email: "a@b.c",
        password: "pw123456789012",
      });
    });

    it("me GETs /api/auth/me", async () => {
      await authApi.me();
      const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock
        .calls[0];
      expect(call[0]).toBe("/api/auth/me");
    });

    it("logout POSTs /api/auth/logout", async () => {
      await authApi.logout();
      const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock
        .calls[0];
      expect(call[0]).toBe("/api/auth/logout");
      expect(call[1].method).toBe("POST");
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/features/auth/api.test.ts`
  Expected: FAIL with `Cannot find module './api'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/features/auth/api.ts`:
  ```ts
  import type { LoginResponse, User } from "./types";

  async function jsonFetch<T>(
    url: string,
    init: RequestInit = {},
  ): Promise<T> {
    const res = await fetch(url, {
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(init.headers || {}) },
      ...init,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? res.statusText);
    }
    return res.json() as Promise<T>;
  }

  export const authApi = {
    register: (email: string, password: string) =>
      jsonFetch<{ message: string }>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),

    login: (email: string, password: string) =>
      jsonFetch<LoginResponse>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),

    loginTwoFactor: (challenge_id: string, code: string) =>
      jsonFetch<LoginResponse>("/api/auth/login/2fa", {
        method: "POST",
        body: JSON.stringify({ challenge_id, code }),
      }),

    logout: () =>
      jsonFetch<{ ok: true }>("/api/auth/logout", { method: "POST" }),

    me: () => jsonFetch<User>("/api/auth/me"),

    resendVerification: (email: string) =>
      jsonFetch<{ message: string }>("/api/auth/resend-verification", {
        method: "POST",
        body: JSON.stringify({ email }),
      }),

    verifyEmail: (token: string) =>
      jsonFetch<{ ok: true }>("/api/auth/verify-email", {
        method: "POST",
        body: JSON.stringify({ token }),
      }),

    requestPasswordReset: (email: string) =>
      jsonFetch<{ message: string }>("/api/auth/password/reset/request", {
        method: "POST",
        body: JSON.stringify({ email }),
      }),

    confirmPasswordReset: (token: string, new_password: string) =>
      jsonFetch<{ ok: true }>("/api/auth/password/reset/confirm", {
        method: "POST",
        body: JSON.stringify({ token, new_password }),
      }),

    changePassword: (current_password: string, new_password: string) =>
      jsonFetch<{ ok: true }>("/api/auth/password/change", {
        method: "POST",
        body: JSON.stringify({ current_password, new_password }),
      }),
  };
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/features/auth/api.test.ts`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/features/auth/api.ts frontend/src/features/auth/api.test.ts
  git commit -m "feat(auth-ui): add authApi client wrapper"
  ```

### Task 7.3: AuthProvider context

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/providers/AuthProvider.test.tsx`:
  ```tsx
  import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
  import { render, screen, waitFor } from "@testing-library/react";
  import { AuthProvider, useAuthContext } from "./AuthProvider";

  function Probe() {
    const { state } = useAuthContext();
    return <div data-testid="status">{state.status}</div>;
  }

  describe("AuthProvider", () => {
    afterEach(() => vi.restoreAllMocks());

    it("loads /api/auth/me on mount and becomes authenticated", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(
          JSON.stringify({
            id: "u1",
            email: "a@b.c",
            role: "user",
            totp_enabled: false,
            created_at: "2026-04-13T00:00:00Z",
          }),
          { status: 200 },
        ),
      );
      render(
        <AuthProvider>
          <Probe />
        </AuthProvider>,
      );
      await waitFor(() =>
        expect(screen.getByTestId("status").textContent).toBe("authenticated"),
      );
    });

    it("marks unauthenticated when /api/auth/me returns 401", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response("{}", { status: 401 }),
      );
      render(
        <AuthProvider>
          <Probe />
        </AuthProvider>,
      );
      await waitFor(() =>
        expect(screen.getByTestId("status").textContent).toBe(
          "unauthenticated",
        ),
      );
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/providers/AuthProvider.test.tsx`
  Expected: FAIL with `Cannot find module './AuthProvider'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/providers/AuthProvider.tsx`:
  ```tsx
  "use client";

  import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useState,
    type ReactNode,
  } from "react";
  import type { AuthState, User } from "@/features/auth/types";
  import { authApi } from "@/features/auth/api";

  interface AuthContextValue {
    state: AuthState;
    login: (email: string, password: string) => Promise<void>;
    logout: () => Promise<void>;
    refresh: () => Promise<void>;
  }

  const AuthContext = createContext<AuthContextValue | null>(null);

  export function AuthProvider({ children }: { children: ReactNode }) {
    const [state, setState] = useState<AuthState>({ status: "loading" });

    const refresh = useCallback(async () => {
      try {
        const user: User = await authApi.me();
        setState({ status: "authenticated", user });
      } catch {
        setState({ status: "unauthenticated" });
      }
    }, []);

    useEffect(() => {
      void refresh();
    }, [refresh]);

    const login = useCallback(
      async (email: string, password: string) => {
        await authApi.login(email, password);
        await refresh();
      },
      [refresh],
    );

    const logout = useCallback(async () => {
      await authApi.logout().catch(() => {});
      setState({ status: "unauthenticated" });
    }, []);

    return (
      <AuthContext.Provider value={{ state, login, logout, refresh }}>
        {children}
      </AuthContext.Provider>
    );
  }

  export function useAuthContext(): AuthContextValue {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuthContext must be used within AuthProvider");
    return ctx;
  }
  ```
  Create `frontend/src/features/auth/hooks/useAuth.ts`:
  ```ts
  "use client";
  export { useAuthContext as useAuth } from "@/providers/AuthProvider";
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/providers/AuthProvider.test.tsx`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/providers/AuthProvider.tsx frontend/src/providers/AuthProvider.test.tsx frontend/src/features/auth/hooks/useAuth.ts
  git commit -m "feat(auth-ui): add AuthProvider context and useAuth hook"
  ```

### Task 7.4: Login Route Handler sets httpOnly cookies

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/app/api/auth/login/route.test.ts`:
  ```ts
  import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
  import { POST } from "./route";

  describe("POST /api/auth/login Route Handler", () => {
    beforeEach(() => {
      process.env.BACKEND_URL = "http://localhost:8001";
    });
    afterEach(() => vi.restoreAllMocks());

    it("sets access_token, refresh_token, user_role cookies on success", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(
          JSON.stringify({
            access_token: "AT",
            refresh_token: "RT",
            user: {
              id: "u1",
              email: "a@b.c",
              role: "admin",
              totp_enabled: false,
              created_at: "",
            },
          }),
          { status: 200 },
        ),
      );

      const req = new Request("http://localhost:3000/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: "a@b.c", password: "pw1234567890" }),
      });
      const res = await POST(req);
      expect(res.status).toBe(200);

      const cookies = res.headers.getSetCookie();
      const all = cookies.join("\n");
      expect(all).toContain("access_token=AT");
      expect(all).toContain("refresh_token=RT");
      expect(all).toContain("user_role=admin");
      expect(all).toContain("HttpOnly");
      expect(all).toContain("SameSite=Lax");
      expect(all).toContain("Path=/");
    });

    it("forwards 2fa_required response without setting cookies", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(
          JSON.stringify({ step: "2fa_required", challenge_id: "c1" }),
          { status: 200 },
        ),
      );
      const req = new Request("http://localhost:3000/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: "a@b.c", password: "pw1234567890" }),
      });
      const res = await POST(req);
      const body = await res.json();
      expect(body).toEqual({ step: "2fa_required", challenge_id: "c1" });
      expect(res.headers.getSetCookie()).toEqual([]);
    });

    it("forwards backend error status", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify({ detail: "Invalid" }), { status: 401 }),
      );
      const req = new Request("http://localhost:3000/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: "a@b.c", password: "wrong" }),
      });
      const res = await POST(req);
      expect(res.status).toBe(401);
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/app/api/auth/login/route.test.ts`
  Expected: FAIL with `Cannot find module './route'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/app/api/auth/login/route.ts`:
  ```ts
  import { NextResponse } from "next/server";

  const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8001";
  const IS_PROD = process.env.NODE_ENV === "production";

  const ACCESS_MAX_AGE = 60 * 15;
  const REFRESH_MAX_AGE = 60 * 60 * 24 * 7;

  export async function POST(req: Request): Promise<Response> {
    const body = await req.text();
    const upstream = await fetch(`${BACKEND}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });

    const text = await upstream.text();
    if (!upstream.ok) {
      return new NextResponse(text, {
        status: upstream.status,
        headers: { "Content-Type": "application/json" },
      });
    }

    const payload = JSON.parse(text);
    if (payload.step === "2fa_required") {
      return NextResponse.json(payload);
    }

    const res = NextResponse.json({ user: payload.user });
    res.cookies.set("access_token", payload.access_token, {
      httpOnly: true,
      secure: IS_PROD,
      sameSite: "lax",
      path: "/",
      maxAge: ACCESS_MAX_AGE,
    });
    res.cookies.set("refresh_token", payload.refresh_token, {
      httpOnly: true,
      secure: IS_PROD,
      sameSite: "lax",
      path: "/",
      maxAge: REFRESH_MAX_AGE,
    });
    res.cookies.set("user_role", payload.user.role, {
      httpOnly: false,
      secure: IS_PROD,
      sameSite: "lax",
      path: "/",
      maxAge: REFRESH_MAX_AGE,
    });
    return res;
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/app/api/auth/login/route.test.ts`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/app/api/auth/login/route.ts frontend/src/app/api/auth/login/route.test.ts
  git commit -m "feat(auth-ui): add login Route Handler with httpOnly cookie proxy"
  ```

### Task 7.5: 2FA login Route Handler

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/app/api/auth/login/2fa/route.test.ts`:
  ```ts
  import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
  import { POST } from "./route";

  describe("POST /api/auth/login/2fa Route Handler", () => {
    beforeEach(() => {
      process.env.BACKEND_URL = "http://localhost:8001";
    });
    afterEach(() => vi.restoreAllMocks());

    it("sets cookies on successful 2FA verification", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(
          JSON.stringify({
            access_token: "AT2",
            refresh_token: "RT2",
            user: {
              id: "u1",
              email: "a@b.c",
              role: "user",
              totp_enabled: true,
              created_at: "",
            },
          }),
          { status: 200 },
        ),
      );
      const req = new Request("http://localhost:3000/api/auth/login/2fa", {
        method: "POST",
        body: JSON.stringify({ challenge_id: "c1", code: "123456" }),
      });
      const res = await POST(req);
      expect(res.status).toBe(200);
      const all = res.headers.getSetCookie().join("\n");
      expect(all).toContain("access_token=AT2");
      expect(all).toContain("refresh_token=RT2");
      expect(all).toContain("user_role=user");
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/app/api/auth/login/2fa/route.test.ts`
  Expected: FAIL with `Cannot find module './route'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/app/api/auth/login/2fa/route.ts`:
  ```ts
  import { NextResponse } from "next/server";

  const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8001";
  const IS_PROD = process.env.NODE_ENV === "production";
  const ACCESS_MAX_AGE = 60 * 15;
  const REFRESH_MAX_AGE = 60 * 60 * 24 * 7;

  export async function POST(req: Request): Promise<Response> {
    const body = await req.text();
    const upstream = await fetch(`${BACKEND}/auth/login/2fa`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    const text = await upstream.text();
    if (!upstream.ok) {
      return new NextResponse(text, {
        status: upstream.status,
        headers: { "Content-Type": "application/json" },
      });
    }
    const payload = JSON.parse(text);
    const res = NextResponse.json({ user: payload.user });
    res.cookies.set("access_token", payload.access_token, {
      httpOnly: true,
      secure: IS_PROD,
      sameSite: "lax",
      path: "/",
      maxAge: ACCESS_MAX_AGE,
    });
    res.cookies.set("refresh_token", payload.refresh_token, {
      httpOnly: true,
      secure: IS_PROD,
      sameSite: "lax",
      path: "/",
      maxAge: REFRESH_MAX_AGE,
    });
    res.cookies.set("user_role", payload.user.role, {
      httpOnly: false,
      secure: IS_PROD,
      sameSite: "lax",
      path: "/",
      maxAge: REFRESH_MAX_AGE,
    });
    return res;
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/app/api/auth/login/2fa/route.test.ts`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/app/api/auth/login/2fa/route.ts frontend/src/app/api/auth/login/2fa/route.test.ts
  git commit -m "feat(auth-ui): add 2FA login Route Handler"
  ```

### Task 7.6: Logout Route Handler clears cookies

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/app/api/auth/logout/route.test.ts`:
  ```ts
  import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
  import { POST } from "./route";

  describe("POST /api/auth/logout Route Handler", () => {
    beforeEach(() => {
      process.env.BACKEND_URL = "http://localhost:8001";
    });
    afterEach(() => vi.restoreAllMocks());

    it("clears access_token, refresh_token, user_role cookies", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify({ ok: true }), { status: 200 }),
      );
      const req = new Request("http://localhost:3000/api/auth/logout", {
        method: "POST",
        headers: { cookie: "refresh_token=RT; access_token=AT" },
      });
      const res = await POST(req);
      expect(res.status).toBe(200);
      const all = res.headers.getSetCookie().join("\n");
      expect(all).toMatch(/access_token=;/);
      expect(all).toMatch(/refresh_token=;/);
      expect(all).toMatch(/user_role=;/);
      expect(all).toContain("Max-Age=0");
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/app/api/auth/logout/route.test.ts`
  Expected: FAIL with `Cannot find module './route'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/app/api/auth/logout/route.ts`:
  ```ts
  import { NextResponse } from "next/server";

  const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8001";
  const IS_PROD = process.env.NODE_ENV === "production";

  export async function POST(req: Request): Promise<Response> {
    const cookieHeader = req.headers.get("cookie") ?? "";
    await fetch(`${BACKEND}/auth/logout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        cookie: cookieHeader,
      },
      body: JSON.stringify({}),
    }).catch(() => null);

    const res = NextResponse.json({ ok: true });
    const clear = {
      httpOnly: true,
      secure: IS_PROD,
      sameSite: "lax" as const,
      path: "/",
      maxAge: 0,
      value: "",
    };
    res.cookies.set("access_token", clear.value, clear);
    res.cookies.set("refresh_token", clear.value, clear);
    res.cookies.set("user_role", "", {
      httpOnly: false,
      secure: IS_PROD,
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });
    return res;
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/app/api/auth/logout/route.test.ts`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/app/api/auth/logout/route.ts frontend/src/app/api/auth/logout/route.test.ts
  git commit -m "feat(auth-ui): add logout Route Handler that clears cookies"
  ```

### Task 7.7: Refresh Route Handler rotates cookies

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/app/api/auth/refresh/route.test.ts`:
  ```ts
  import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
  import { POST } from "./route";

  describe("POST /api/auth/refresh Route Handler", () => {
    beforeEach(() => {
      process.env.BACKEND_URL = "http://localhost:8001";
    });
    afterEach(() => vi.restoreAllMocks());

    it("rotates access_token and refresh_token cookies", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(
          JSON.stringify({ access_token: "AT_NEW", refresh_token: "RT_NEW" }),
          { status: 200 },
        ),
      );
      const req = new Request("http://localhost:3000/api/auth/refresh", {
        method: "POST",
        headers: { cookie: "refresh_token=RT_OLD" },
      });
      const res = await POST(req);
      expect(res.status).toBe(200);
      const all = res.headers.getSetCookie().join("\n");
      expect(all).toContain("access_token=AT_NEW");
      expect(all).toContain("refresh_token=RT_NEW");
    });

    it("returns 401 and does not set cookies when backend refuses", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response("{}", { status: 401 }),
      );
      const req = new Request("http://localhost:3000/api/auth/refresh", {
        method: "POST",
        headers: { cookie: "refresh_token=BAD" },
      });
      const res = await POST(req);
      expect(res.status).toBe(401);
      expect(res.headers.getSetCookie()).toEqual([]);
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/app/api/auth/refresh/route.test.ts`
  Expected: FAIL with `Cannot find module './route'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/app/api/auth/refresh/route.ts`:
  ```ts
  import { NextResponse } from "next/server";

  const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8001";
  const IS_PROD = process.env.NODE_ENV === "production";
  const ACCESS_MAX_AGE = 60 * 15;
  const REFRESH_MAX_AGE = 60 * 60 * 24 * 7;

  function readCookie(header: string | null, name: string): string | null {
    if (!header) return null;
    const match = header.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
    return match ? decodeURIComponent(match[1]) : null;
  }

  export async function POST(req: Request): Promise<Response> {
    const refresh = readCookie(req.headers.get("cookie"), "refresh_token");
    if (!refresh) {
      return new NextResponse(JSON.stringify({ detail: "no refresh token" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }

    const upstream = await fetch(`${BACKEND}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });

    if (!upstream.ok) {
      return new NextResponse(await upstream.text(), {
        status: upstream.status,
        headers: { "Content-Type": "application/json" },
      });
    }

    const payload = await upstream.json();
    const res = NextResponse.json({ ok: true });
    res.cookies.set("access_token", payload.access_token, {
      httpOnly: true,
      secure: IS_PROD,
      sameSite: "lax",
      path: "/",
      maxAge: ACCESS_MAX_AGE,
    });
    res.cookies.set("refresh_token", payload.refresh_token, {
      httpOnly: true,
      secure: IS_PROD,
      sameSite: "lax",
      path: "/",
      maxAge: REFRESH_MAX_AGE,
    });
    return res;
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/app/api/auth/refresh/route.test.ts`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/app/api/auth/refresh/route.ts frontend/src/app/api/auth/refresh/route.test.ts
  git commit -m "feat(auth-ui): add refresh Route Handler with cookie rotation"
  ```

### Task 7.8: Register, me, and catch-all Route Handlers

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/app/api/auth/register/route.test.ts`:
  ```ts
  import { describe, it, expect, vi, afterEach } from "vitest";
  import { POST } from "./route";

  describe("POST /api/auth/register Route Handler", () => {
    afterEach(() => vi.restoreAllMocks());

    it("forwards to backend and returns status", async () => {
      const spy = vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify({ message: "Check email" }), {
          status: 201,
        }),
      );
      const req = new Request("http://localhost:3000/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ email: "x@y.z", password: "pw1234567890" }),
      });
      const res = await POST(req);
      expect(res.status).toBe(201);
      expect(spy.mock.calls[0][0]).toContain("/auth/register");
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/app/api/auth/register/route.test.ts`
  Expected: FAIL with `Cannot find module './route'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/app/api/auth/register/route.ts`:
  ```ts
  import { NextResponse } from "next/server";

  const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8001";

  export async function POST(req: Request): Promise<Response> {
    const body = await req.text();
    const upstream = await fetch(`${BACKEND}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    return new NextResponse(await upstream.text(), {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  }
  ```
  Create `frontend/src/app/api/auth/me/route.ts`:
  ```ts
  import { NextResponse } from "next/server";

  const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8001";

  function readCookie(header: string | null, name: string): string | null {
    if (!header) return null;
    const match = header.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
    return match ? decodeURIComponent(match[1]) : null;
  }

  export async function GET(req: Request): Promise<Response> {
    const access = readCookie(req.headers.get("cookie"), "access_token");
    if (!access) {
      return new NextResponse(JSON.stringify({ detail: "unauthenticated" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }
    const upstream = await fetch(`${BACKEND}/auth/me`, {
      headers: { Authorization: `Bearer ${access}` },
    });
    return new NextResponse(await upstream.text(), {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  }
  ```
  Create `frontend/src/app/api/auth/[...rest]/route.ts`:
  ```ts
  import { NextResponse } from "next/server";

  const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8001";

  function readCookie(header: string | null, name: string): string | null {
    if (!header) return null;
    const match = header.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
    return match ? decodeURIComponent(match[1]) : null;
  }

  async function forward(
    req: Request,
    ctx: { params: Promise<{ rest: string[] }> },
  ): Promise<Response> {
    const { rest } = await ctx.params;
    const path = "/" + rest.join("/");
    const url = new URL(req.url);
    const target = `${BACKEND}/auth${path}${url.search}`;
    const access = readCookie(req.headers.get("cookie"), "access_token");

    const headers: Record<string, string> = {
      "Content-Type": req.headers.get("content-type") ?? "application/json",
    };
    if (access) headers.Authorization = `Bearer ${access}`;

    const init: RequestInit = { method: req.method, headers };
    if (req.method !== "GET" && req.method !== "HEAD") {
      init.body = await req.text();
    }

    const upstream = await fetch(target, init);
    return new NextResponse(await upstream.text(), {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  export const GET = forward;
  export const POST = forward;
  export const PUT = forward;
  export const DELETE = forward;
  export const PATCH = forward;
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/app/api/auth/register/route.test.ts`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/app/api/auth/register frontend/src/app/api/auth/me frontend/src/app/api/auth/\[...rest\]
  git commit -m "feat(auth-ui): add register, me, and catch-all auth Route Handlers"
  ```

### Task 7.9: Edge middleware for protected and admin routes

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/middleware.test.ts`:
  ```ts
  import { describe, it, expect } from "vitest";
  import { NextRequest } from "next/server";
  import { middleware } from "./middleware";

  function makeReq(path: string, cookies: Record<string, string> = {}) {
    const url = new URL(`http://localhost:3000${path}`);
    const req = new NextRequest(url);
    for (const [k, v] of Object.entries(cookies)) {
      req.cookies.set(k, v);
    }
    return req;
  }

  describe("middleware", () => {
    it("redirects to /login when protected route has no access_token", () => {
      const res = middleware(makeReq("/reports"));
      expect(res.status).toBe(307);
      expect(res.headers.get("location")).toContain("/login?next=%2Freports");
    });

    it("redirects authenticated users away from /login to /", () => {
      const res = middleware(makeReq("/login", { access_token: "AT" }));
      expect(res.headers.get("location")).toBe("http://localhost:3000/");
    });

    it("redirects /admin/* to / when user_role != admin", () => {
      const res = middleware(
        makeReq("/admin/audit", { access_token: "AT", user_role: "user" }),
      );
      expect(res.headers.get("location")).toBe("http://localhost:3000/");
    });

    it("allows /admin/* when user_role=admin", () => {
      const res = middleware(
        makeReq("/admin/audit", { access_token: "AT", user_role: "admin" }),
      );
      expect(res.headers.get("location")).toBeNull();
    });

    it("lets anonymous users through on public pages", () => {
      const res = middleware(makeReq("/login"));
      expect(res.headers.get("location")).toBeNull();
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/middleware.test.ts`
  Expected: FAIL with `Cannot find module './middleware'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/middleware.ts`:
  ```ts
  import { NextResponse, type NextRequest } from "next/server";

  const PUBLIC_PATHS = [
    "/login",
    "/register",
    "/verify-email",
    "/forgot-password",
    "/reset-password",
  ];

  function isPublic(pathname: string): boolean {
    return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"));
  }

  function isAdmin(pathname: string): boolean {
    return pathname === "/admin" || pathname.startsWith("/admin/");
  }

  export function middleware(req: NextRequest): NextResponse {
    const { pathname } = req.nextUrl;
    const access = req.cookies.get("access_token")?.value;
    const role = req.cookies.get("user_role")?.value;

    if (access && isPublic(pathname)) {
      return NextResponse.redirect(new URL("/", req.url));
    }

    if (isPublic(pathname)) {
      return NextResponse.next();
    }

    if (!access) {
      const loginUrl = new URL("/login", req.url);
      loginUrl.searchParams.set("next", pathname);
      return NextResponse.redirect(loginUrl);
    }

    if (isAdmin(pathname) && role !== "admin") {
      return NextResponse.redirect(new URL("/", req.url));
    }

    return NextResponse.next();
  }

  export const config = {
    matcher: [
      "/((?!_next/static|_next/image|favicon.ico|api/).*)",
    ],
  };
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/middleware.test.ts`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/middleware.ts frontend/src/middleware.test.ts
  git commit -m "feat(auth-ui): add edge middleware for protected and admin routes"
  ```

### Task 7.10: Single-flight 401 interceptor in lib/api.ts

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/lib/api.interceptor.test.ts`:
  ```ts
  import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
  import { apiCall, __resetRefreshForTest } from "./api";

  describe("apiCall single-flight 401 interceptor", () => {
    beforeEach(() => {
      __resetRefreshForTest();
    });
    afterEach(() => vi.restoreAllMocks());

    it("triggers single refresh on 401 and retries once", async () => {
      const fetchMock = vi.fn<typeof fetch>();
      fetchMock
        .mockResolvedValueOnce(new Response("", { status: 401 }))
        .mockResolvedValueOnce(new Response("{}", { status: 200 }))
        .mockResolvedValueOnce(new Response("ok", { status: 200 }));
      vi.stubGlobal("fetch", fetchMock);

      const res = await apiCall("/reports");
      expect(res.status).toBe(200);
      expect(fetchMock).toHaveBeenCalledTimes(3);
      expect(fetchMock.mock.calls[1][0]).toBe("/api/auth/refresh");
    });

    it("parallel 401s share exactly one refresh", async () => {
      const fetchMock = vi.fn<typeof fetch>((url: RequestInfo | URL) => {
        const u = typeof url === "string" ? url : url.toString();
        if (u === "/api/auth/refresh")
          return Promise.resolve(new Response("{}", { status: 200 }));
        // first call 401, subsequent (retry) 200
        return Promise.resolve(new Response("", { status: 401 }));
      });
      vi.stubGlobal("fetch", fetchMock);

      const calls = await Promise.allSettled([
        apiCall("/reports"),
        apiCall("/sessions"),
        apiCall("/therapy-plans"),
      ]);
      expect(calls).toHaveLength(3);
      const refreshCalls = fetchMock.mock.calls.filter(
        (c) => c[0] === "/api/auth/refresh",
      );
      expect(refreshCalls).toHaveLength(1);
    });

    it("redirects to /login when refresh fails", async () => {
      const hrefSetter = vi.fn();
      Object.defineProperty(window, "location", {
        value: { href: "", set href(v: string) { hrefSetter(v); } },
        writable: true,
      });
      const fetchMock = vi.fn<typeof fetch>();
      fetchMock
        .mockResolvedValueOnce(new Response("", { status: 401 }))
        .mockResolvedValueOnce(new Response("", { status: 401 }));
      vi.stubGlobal("fetch", fetchMock);

      await apiCall("/reports");
      expect(hrefSetter).toHaveBeenCalledWith("/login");
    });

    it("bypasses interceptor for /api/auth/* URLs", async () => {
      const fetchMock = vi.fn<typeof fetch>();
      fetchMock.mockResolvedValue(new Response("", { status: 401 }));
      vi.stubGlobal("fetch", fetchMock);

      const res = await apiCall("/api/auth/login");
      expect(res.status).toBe(401);
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/lib/api.interceptor.test.ts`
  Expected: FAIL with `__resetRefreshForTest is not exported`.
- [ ] **Step 3: Implement**
  Append to `frontend/src/lib/api.ts` (top of file, before existing `fetchApi`):
  ```ts
  // ============ Single-flight 401 refresh interceptor ============

  let refreshPromise: Promise<Response> | null = null;

  export function __resetRefreshForTest(): void {
    refreshPromise = null;
  }

  export async function apiCall(
    url: string,
    opts: RequestInit = {},
  ): Promise<Response> {
    const res = await fetch(url, { credentials: "include", ...opts });
    if (res.status !== 401 || url.includes("/api/auth/")) {
      return res;
    }

    if (!refreshPromise) {
      refreshPromise = fetch("/api/auth/refresh", {
        method: "POST",
        credentials: "include",
      }).finally(() => {
        setTimeout(() => {
          refreshPromise = null;
        }, 0);
      });
    }

    const refreshed = await refreshPromise;
    if (refreshed.ok) {
      return fetch(url, { credentials: "include", ...opts });
    }
    window.location.href = "/login";
    return res;
  }
  ```
  And update `fetchApi` to call through `apiCall` by replacing the `fetch(...)` line:
  ```ts
  async function fetchApi<T>(
    path: string,
    init?: RequestInit,
  ): Promise<T> {
    const res = await apiCall(`${API}${path}`, init);
    if (!res.ok) {
      const detail = await res.json().catch(() => null);
      throw new Error(detail?.detail ?? res.statusText);
    }
    return res.json();
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/lib/api.interceptor.test.ts`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/lib/api.ts frontend/src/lib/api.interceptor.test.ts
  git commit -m "feat(auth-ui): add single-flight 401 refresh interceptor to api client"
  ```

### Task 7.11: Wire AuthProvider into root layout and carve out /api/auth from proxy

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/app/layout.authwrap.test.tsx`:
  ```tsx
  import { describe, it, expect } from "vitest";
  import { readFileSync } from "node:fs";

  describe("root layout wires AuthProvider", () => {
    it("imports AuthProvider and wraps children", () => {
      const src = readFileSync(
        new URL("./layout.tsx", import.meta.url),
        "utf8",
      );
      expect(src).toContain("AuthProvider");
      expect(src).toMatch(/<AuthProvider>[\s\S]*children[\s\S]*<\/AuthProvider>/);
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/app/layout.authwrap.test.tsx`
  Expected: FAIL (AuthProvider not referenced yet in layout).
- [ ] **Step 3: Implement**
  Modify `frontend/src/app/layout.tsx` — add `import { AuthProvider } from "@/providers/AuthProvider";` and wrap the existing provider tree:
  ```tsx
  <AuthProvider>
    {children}
  </AuthProvider>
  ```
  Modify `frontend/next.config.ts` to exclude `/api/auth/*` from the backend passthrough. Replace the rewrites block with:
  ```ts
  async rewrites() {
    return [
      {
        source: "/api/:path((?!auth).*)",
        destination: `${process.env.BACKEND_URL ?? "http://localhost:8001"}/:path*`,
      },
    ];
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/app/layout.authwrap.test.tsx`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/app/layout.tsx frontend/next.config.ts frontend/src/app/layout.authwrap.test.tsx
  git commit -m "feat(auth-ui): wrap root layout with AuthProvider and carve out /api/auth from proxy"
  ```

### Task 7.12: Opus Gate 7A — Cookie + Single-Flight Refresh Review

- [ ] **Step 1: Invoke Opus reviewer**
  ```
  Agent({
    subagent_type: "general-purpose",
    model: "opus",
    description: "Opus security review: cookie + single-flight refresh",
    prompt: "Review frontend/src/app/api/auth/login/route.ts, frontend/src/app/api/auth/login/2fa/route.ts, frontend/src/app/api/auth/refresh/route.ts, frontend/src/app/api/auth/logout/route.ts. Verify cookie attributes: httpOnly for access_token and refresh_token, user_role is NOT httpOnly (edge middleware needs to read it), Secure is true in production and false in dev, SameSite=Lax, Path=/, access_token Max-Age=900s, refresh_token Max-Age=604800s, logout sets Max-Age=0 for all three. Also review frontend/src/lib/api.ts single-flight refresh: (1) the refreshPromise is invalidated whether the refresh succeeds or fails so a subsequent 401 can start a new refresh, (2) there is no infinite loop if the refresh itself returns 401 (the interceptor bypass on /api/auth/* URLs must handle this), (3) parallel callers all resolve from the same shared promise, (4) window.location.href='/login' is reached on refresh failure. Finally review frontend/src/middleware.ts matcher and logic: (a) the matcher correctly excludes /_next and /api/, (b) the isAdmin('/admin') does not false-positive on a path like /administrators, (c) isPublic correctly identifies /verify-email but NOT /verify-email-extra, (d) the redirect to /login includes ?next= with the original pathname URL-encoded. Report any issues as specific file:line findings."
  })
  ```
- [ ] **Step 2: Address any findings**
  Fix each reported issue with a new TDD cycle (failing test → fix → pass → commit with `fix(auth-ui):` scope).

---

## Phase 8: Frontend Auth Pages

**Goal:** Build the five public auth pages (login, register, verify-email, forgot-password, reset-password) with generic error messages and server-authoritative validation.

**Files:**
- Create: `frontend/src/app/(auth)/layout.tsx`
- Create: `frontend/src/app/(auth)/login/page.tsx`
- Create: `frontend/src/app/(auth)/register/page.tsx`
- Create: `frontend/src/app/(auth)/verify-email/page.tsx`
- Create: `frontend/src/app/(auth)/forgot-password/page.tsx`
- Create: `frontend/src/app/(auth)/reset-password/page.tsx`
- Create: `frontend/src/features/auth/components/LoginForm.tsx`
- Create: `frontend/src/features/auth/components/LoginForm.test.tsx`
- Create: `frontend/src/features/auth/components/RegisterForm.tsx`
- Create: `frontend/src/features/auth/components/RegisterForm.test.tsx`
- Create: `frontend/src/features/auth/components/PasswordStrengthMeter.tsx`
- Create: `frontend/src/features/auth/components/PasswordStrengthMeter.test.tsx`
- Create: `frontend/src/features/auth/components/TwoFactorChallenge.tsx`
- Create: `frontend/src/features/auth/components/TwoFactorChallenge.test.tsx`
- Create: `frontend/src/features/auth/hooks/useLogin.ts`
- Create: `frontend/src/features/auth/hooks/useRegister.ts`
- Create: `frontend/src/app/(auth)/verify-email/page.test.tsx`
- Create: `frontend/src/app/(auth)/forgot-password/page.test.tsx`
- Create: `frontend/src/app/(auth)/reset-password/page.test.tsx`
- Modify: `frontend/package.json`

### Task 8.1: Add zxcvbn-ts dependency and (auth) layout

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/app/(auth)/layout.test.tsx`:
  ```tsx
  import { describe, it, expect } from "vitest";
  import { render, screen } from "@testing-library/react";
  import AuthLayout from "./layout";

  describe("(auth) layout", () => {
    it("renders children inside a centered card wrapper", () => {
      render(
        <AuthLayout>
          <div data-testid="child">hello</div>
        </AuthLayout>,
      );
      expect(screen.getByTestId("child")).toBeInTheDocument();
      const card = screen.getByTestId("auth-card");
      expect(card).toBeInTheDocument();
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- "src/app/(auth)/layout.test.tsx"`
  Expected: FAIL with `Cannot find module './layout'`.
- [ ] **Step 3: Implement**
  Install deps:
  ```bash
  cd frontend && npm install @zxcvbn-ts/core @zxcvbn-ts/language-common
  ```
  Create `frontend/src/app/(auth)/layout.tsx`:
  ```tsx
  import type { ReactNode } from "react";

  export default function AuthLayout({ children }: { children: ReactNode }) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-neutral-50 dark:bg-neutral-950 p-4">
        <div
          data-testid="auth-card"
          className="w-full max-w-md rounded-2xl bg-white dark:bg-neutral-900 shadow-lg p-8"
        >
          {children}
        </div>
      </div>
    );
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- "src/app/(auth)/layout.test.tsx"`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/package.json frontend/package-lock.json "frontend/src/app/(auth)/layout.tsx" "frontend/src/app/(auth)/layout.test.tsx"
  git commit -m "feat(auth-ui): add (auth) route group layout and zxcvbn-ts dependency"
  ```

### Task 8.2: PasswordStrengthMeter component

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/features/auth/components/PasswordStrengthMeter.test.tsx`:
  ```tsx
  import { describe, it, expect } from "vitest";
  import { render, screen } from "@testing-library/react";
  import { PasswordStrengthMeter } from "./PasswordStrengthMeter";

  describe("PasswordStrengthMeter", () => {
    it("renders a score bar with aria-valuenow between 0 and 4", () => {
      render(<PasswordStrengthMeter password="hello" />);
      const bar = screen.getByRole("progressbar");
      const v = Number(bar.getAttribute("aria-valuenow"));
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThanOrEqual(4);
    });

    it("renders a stronger score for a longer password", () => {
      const { rerender } = render(<PasswordStrengthMeter password="a" />);
      const weak = Number(
        screen.getByRole("progressbar").getAttribute("aria-valuenow"),
      );
      rerender(
        <PasswordStrengthMeter password="correct horse battery staple 2026!" />,
      );
      const strong = Number(
        screen.getByRole("progressbar").getAttribute("aria-valuenow"),
      );
      expect(strong).toBeGreaterThanOrEqual(weak);
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/features/auth/components/PasswordStrengthMeter.test.tsx`
  Expected: FAIL with `Cannot find module './PasswordStrengthMeter'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/features/auth/components/PasswordStrengthMeter.tsx`:
  ```tsx
  "use client";

  import { useEffect, useMemo, useState } from "react";
  import { zxcvbn, zxcvbnOptions } from "@zxcvbn-ts/core";
  import * as zxcvbnCommon from "@zxcvbn-ts/language-common";

  zxcvbnOptions.setOptions({
    translations: zxcvbnCommon.translations,
    graphs: zxcvbnCommon.adjacencyGraphs,
    dictionary: zxcvbnCommon.dictionary,
  });

  const LABELS = ["Sehr schwach", "Schwach", "Okay", "Gut", "Stark"];
  const COLORS = [
    "bg-red-500",
    "bg-orange-500",
    "bg-yellow-500",
    "bg-lime-500",
    "bg-green-500",
  ];

  export function PasswordStrengthMeter({ password }: { password: string }) {
    const [score, setScore] = useState(0);

    useEffect(() => {
      if (!password) {
        setScore(0);
        return;
      }
      const result = zxcvbn(password);
      setScore(result.score);
    }, [password]);

    const label = useMemo(() => LABELS[score], [score]);

    return (
      <div className="mt-2">
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={4}
          aria-valuenow={score}
          aria-label="Passwortstärke"
          className="h-2 w-full bg-neutral-200 dark:bg-neutral-800 rounded"
        >
          <div
            className={`h-full rounded ${COLORS[score]}`}
            style={{ width: `${(score / 4) * 100}%` }}
          />
        </div>
        <p className="text-xs mt-1 text-neutral-600 dark:text-neutral-400">
          {label}
        </p>
      </div>
    );
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/features/auth/components/PasswordStrengthMeter.test.tsx`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/features/auth/components/PasswordStrengthMeter.tsx frontend/src/features/auth/components/PasswordStrengthMeter.test.tsx
  git commit -m "feat(auth-ui): add PasswordStrengthMeter with zxcvbn-ts"
  ```

### Task 8.3: TwoFactorChallenge component

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/features/auth/components/TwoFactorChallenge.test.tsx`:
  ```tsx
  import { describe, it, expect, vi } from "vitest";
  import { render, screen, fireEvent } from "@testing-library/react";
  import { TwoFactorChallenge } from "./TwoFactorChallenge";

  describe("TwoFactorChallenge", () => {
    it("calls onSubmit with a 6-digit code", () => {
      const onSubmit = vi.fn();
      render(<TwoFactorChallenge onSubmit={onSubmit} loading={false} />);
      const input = screen.getByLabelText(/6-stelliger Code/i);
      fireEvent.change(input, { target: { value: "123456" } });
      fireEvent.click(screen.getByRole("button", { name: /bestätigen/i }));
      expect(onSubmit).toHaveBeenCalledWith("123456");
    });

    it("disables submit when code length != 6", () => {
      render(<TwoFactorChallenge onSubmit={() => {}} loading={false} />);
      const btn = screen.getByRole("button", { name: /bestätigen/i });
      fireEvent.change(screen.getByLabelText(/6-stelliger Code/i), {
        target: { value: "12345" },
      });
      expect(btn).toBeDisabled();
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/features/auth/components/TwoFactorChallenge.test.tsx`
  Expected: FAIL with `Cannot find module './TwoFactorChallenge'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/features/auth/components/TwoFactorChallenge.tsx`:
  ```tsx
  "use client";

  import { useState } from "react";

  interface Props {
    onSubmit: (code: string) => void;
    loading: boolean;
    error?: string | null;
  }

  export function TwoFactorChallenge({ onSubmit, loading, error }: Props) {
    const [code, setCode] = useState("");
    const valid = /^\d{6}$/.test(code);

    return (
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (valid) onSubmit(code);
        }}
      >
        <label className="block">
          <span className="text-sm font-medium">6-stelliger Code</span>
          <input
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            pattern="\d{6}"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900 text-center tracking-widest text-lg"
          />
        </label>
        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={!valid || loading}
          className="w-full rounded bg-blue-600 text-white py-2 disabled:opacity-50"
        >
          Bestätigen
        </button>
      </form>
    );
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/features/auth/components/TwoFactorChallenge.test.tsx`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/features/auth/components/TwoFactorChallenge.tsx frontend/src/features/auth/components/TwoFactorChallenge.test.tsx
  git commit -m "feat(auth-ui): add TwoFactorChallenge 6-digit input component"
  ```

### Task 8.4: LoginForm with 2FA branching

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/features/auth/components/LoginForm.test.tsx`:
  ```tsx
  import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
  import { render, screen, fireEvent, waitFor } from "@testing-library/react";
  import { LoginForm } from "./LoginForm";

  function mockFetch(fn: (url: string, init?: RequestInit) => Response) {
    return vi
      .spyOn(global, "fetch")
      .mockImplementation(async (url, init) =>
        fn(typeof url === "string" ? url : url.toString(), init),
      );
  }

  describe("LoginForm", () => {
    beforeEach(() => {
      Object.defineProperty(window, "location", {
        value: { href: "" },
        writable: true,
      });
    });
    afterEach(() => vi.restoreAllMocks());

    it("submits credentials and redirects on success", async () => {
      mockFetch((url) => {
        if (url.endsWith("/api/auth/login"))
          return new Response(
            JSON.stringify({
              user: {
                id: "u1",
                email: "a@b.c",
                role: "user",
                totp_enabled: false,
                created_at: "",
              },
            }),
            { status: 200 },
          );
        return new Response("", { status: 404 });
      });

      render(<LoginForm />);
      fireEvent.change(screen.getByLabelText(/email/i), {
        target: { value: "a@b.c" },
      });
      fireEvent.change(screen.getByLabelText(/passwort/i), {
        target: { value: "pw1234567890" },
      });
      fireEvent.click(screen.getByRole("button", { name: /anmelden/i }));

      await waitFor(() => expect(window.location.href).toBe("/"));
    });

    it("shows generic error on 401", async () => {
      mockFetch(() => new Response(JSON.stringify({ detail: "x" }), { status: 401 }));
      render(<LoginForm />);
      fireEvent.change(screen.getByLabelText(/email/i), {
        target: { value: "a@b.c" },
      });
      fireEvent.change(screen.getByLabelText(/passwort/i), {
        target: { value: "wrongwrongwrong" },
      });
      fireEvent.click(screen.getByRole("button", { name: /anmelden/i }));
      const err = await screen.findByRole("alert");
      expect(err.textContent).toMatch(/email.*passwort.*falsch/i);
    });

    it("renders 2FA step when backend returns 2fa_required", async () => {
      mockFetch(() =>
        new Response(
          JSON.stringify({ step: "2fa_required", challenge_id: "c1" }),
          { status: 200 },
        ),
      );
      render(<LoginForm />);
      fireEvent.change(screen.getByLabelText(/email/i), {
        target: { value: "a@b.c" },
      });
      fireEvent.change(screen.getByLabelText(/passwort/i), {
        target: { value: "pw1234567890" },
      });
      fireEvent.click(screen.getByRole("button", { name: /anmelden/i }));
      const twoFaInput = await screen.findByLabelText(/6-stelliger Code/i);
      expect(twoFaInput).toBeInTheDocument();
    });

    it("completes login after 2FA code submit", async () => {
      let stage = 0;
      mockFetch((url) => {
        if (url.endsWith("/api/auth/login")) {
          return new Response(
            JSON.stringify({ step: "2fa_required", challenge_id: "c1" }),
            { status: 200 },
          );
        }
        if (url.endsWith("/api/auth/login/2fa")) {
          stage = 1;
          return new Response(
            JSON.stringify({
              user: {
                id: "u1",
                email: "a@b.c",
                role: "user",
                totp_enabled: true,
                created_at: "",
              },
            }),
            { status: 200 },
          );
        }
        return new Response("", { status: 404 });
      });

      render(<LoginForm />);
      fireEvent.change(screen.getByLabelText(/email/i), {
        target: { value: "a@b.c" },
      });
      fireEvent.change(screen.getByLabelText(/passwort/i), {
        target: { value: "pw1234567890" },
      });
      fireEvent.click(screen.getByRole("button", { name: /anmelden/i }));

      const code = await screen.findByLabelText(/6-stelliger Code/i);
      fireEvent.change(code, { target: { value: "123456" } });
      fireEvent.click(screen.getByRole("button", { name: /bestätigen/i }));

      await waitFor(() => expect(stage).toBe(1));
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/features/auth/components/LoginForm.test.tsx`
  Expected: FAIL with `Cannot find module './LoginForm'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/features/auth/hooks/useLogin.ts`:
  ```ts
  "use client";
  import { useState } from "react";
  import { authApi } from "@/features/auth/api";
  import type { LoginResponse } from "@/features/auth/types";

  export function useLogin() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function submit(
      email: string,
      password: string,
    ): Promise<LoginResponse | null> {
      setLoading(true);
      setError(null);
      try {
        const res = await authApi.login(email, password);
        return res;
      } catch {
        setError("Email oder Passwort ist falsch.");
        return null;
      } finally {
        setLoading(false);
      }
    }

    async function submit2fa(
      challenge_id: string,
      code: string,
    ): Promise<LoginResponse | null> {
      setLoading(true);
      setError(null);
      try {
        return await authApi.loginTwoFactor(challenge_id, code);
      } catch {
        setError("Code ist ungültig oder abgelaufen.");
        return null;
      } finally {
        setLoading(false);
      }
    }

    return { submit, submit2fa, loading, error };
  }
  ```
  Create `frontend/src/features/auth/components/LoginForm.tsx`:
  ```tsx
  "use client";

  import { useState } from "react";
  import Link from "next/link";
  import { useLogin } from "../hooks/useLogin";
  import { TwoFactorChallenge } from "./TwoFactorChallenge";

  export function LoginForm() {
    const { submit, submit2fa, loading, error } = useLogin();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [challengeId, setChallengeId] = useState<string | null>(null);

    async function handleSubmit(e: React.FormEvent) {
      e.preventDefault();
      const res = await submit(email, password);
      if (!res) return;
      if ("step" in res && res.step === "2fa_required") {
        setChallengeId(res.challenge_id);
        return;
      }
      window.location.href = "/";
    }

    async function handle2fa(code: string) {
      if (!challengeId) return;
      const res = await submit2fa(challengeId, code);
      if (res && !("step" in res)) {
        window.location.href = "/";
      }
    }

    if (challengeId) {
      return (
        <TwoFactorChallenge
          onSubmit={handle2fa}
          loading={loading}
          error={error}
        />
      );
    }

    return (
      <form className="space-y-4" onSubmit={handleSubmit}>
        <h1 className="text-2xl font-semibold mb-6">Anmelden</h1>
        <label className="block">
          <span className="text-sm font-medium">Email</span>
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Passwort</span>
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
          />
        </label>
        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-blue-600 text-white py-2 disabled:opacity-50"
        >
          Anmelden
        </button>
        <div className="flex justify-between text-sm">
          <Link href="/register" className="text-blue-600 hover:underline">
            Registrieren
          </Link>
          <Link
            href="/forgot-password"
            className="text-blue-600 hover:underline"
          >
            Passwort vergessen?
          </Link>
        </div>
      </form>
    );
  }
  ```
  Create `frontend/src/app/(auth)/login/page.tsx`:
  ```tsx
  import { LoginForm } from "@/features/auth/components/LoginForm";

  export default function LoginPage() {
    return <LoginForm />;
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/features/auth/components/LoginForm.test.tsx`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add "frontend/src/app/(auth)/login/page.tsx" frontend/src/features/auth/hooks/useLogin.ts frontend/src/features/auth/components/LoginForm.tsx frontend/src/features/auth/components/LoginForm.test.tsx
  git commit -m "feat(auth-ui): add LoginForm with inline 2FA branching"
  ```

### Task 8.5: RegisterForm with 12-char floor and strength hint

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/features/auth/components/RegisterForm.test.tsx`:
  ```tsx
  import { describe, it, expect, vi, afterEach } from "vitest";
  import { render, screen, fireEvent, waitFor } from "@testing-library/react";
  import { RegisterForm } from "./RegisterForm";

  describe("RegisterForm", () => {
    afterEach(() => vi.restoreAllMocks());

    it("blocks submit when password < 12 chars", () => {
      render(<RegisterForm />);
      fireEvent.change(screen.getByLabelText(/email/i), {
        target: { value: "a@b.c" },
      });
      fireEvent.change(screen.getByLabelText(/passwort/i), {
        target: { value: "short" },
      });
      const btn = screen.getByRole("button", { name: /registrieren/i });
      expect(btn).toBeDisabled();
    });

    it("allows submit at exactly 12 chars even if weak", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify({ message: "Check email" }), { status: 201 }),
      );
      render(<RegisterForm />);
      fireEvent.change(screen.getByLabelText(/email/i), {
        target: { value: "a@b.c" },
      });
      fireEvent.change(screen.getByLabelText(/passwort/i), {
        target: { value: "aaaaaaaaaaaa" },
      });
      const btn = screen.getByRole("button", { name: /registrieren/i });
      expect(btn).not.toBeDisabled();
    });

    it("shows zxcvbn score progressbar", () => {
      render(<RegisterForm />);
      fireEvent.change(screen.getByLabelText(/passwort/i), {
        target: { value: "correct horse battery staple" },
      });
      expect(screen.getByRole("progressbar")).toBeInTheDocument();
    });

    it("shows check-email message after successful submit", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify({ message: "ok" }), { status: 201 }),
      );
      render(<RegisterForm />);
      fireEvent.change(screen.getByLabelText(/email/i), {
        target: { value: "a@b.c" },
      });
      fireEvent.change(screen.getByLabelText(/passwort/i), {
        target: { value: "pw1234567890ab" },
      });
      fireEvent.click(screen.getByRole("button", { name: /registrieren/i }));
      await waitFor(() =>
        expect(screen.getByText(/email.*bestätig/i)).toBeInTheDocument(),
      );
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/features/auth/components/RegisterForm.test.tsx`
  Expected: FAIL with `Cannot find module './RegisterForm'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/features/auth/hooks/useRegister.ts`:
  ```ts
  "use client";
  import { useState } from "react";
  import { authApi } from "@/features/auth/api";

  export function useRegister() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [done, setDone] = useState(false);

    async function submit(email: string, password: string) {
      setLoading(true);
      setError(null);
      try {
        await authApi.register(email, password);
        setDone(true);
      } catch {
        setError("Registrierung fehlgeschlagen. Bitte später erneut versuchen.");
      } finally {
        setLoading(false);
      }
    }

    return { submit, loading, error, done };
  }
  ```
  Create `frontend/src/features/auth/components/RegisterForm.tsx`:
  ```tsx
  "use client";

  import { useState } from "react";
  import Link from "next/link";
  import { useRegister } from "../hooks/useRegister";
  import { PasswordStrengthMeter } from "./PasswordStrengthMeter";

  export function RegisterForm() {
    const { submit, loading, error, done } = useRegister();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");

    const tooShort = password.length < 12;

    if (done) {
      return (
        <div className="space-y-4">
          <h1 className="text-2xl font-semibold">Fast geschafft</h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Bitte bestätigen Sie Ihre Email-Adresse über den Link, den wir Ihnen
            soeben gesendet haben.
          </p>
          <Link
            href="/login"
            className="block text-center rounded bg-blue-600 text-white py-2"
          >
            Zur Anmeldung
          </Link>
        </div>
      );
    }

    return (
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (!tooShort) submit(email, password);
        }}
      >
        <h1 className="text-2xl font-semibold mb-6">Registrieren</h1>
        <label className="block">
          <span className="text-sm font-medium">Email</span>
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Passwort (min. 12 Zeichen)</span>
          <input
            type="password"
            autoComplete="new-password"
            required
            minLength={12}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
          />
          <PasswordStrengthMeter password={password} />
        </label>
        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={loading || tooShort}
          className="w-full rounded bg-blue-600 text-white py-2 disabled:opacity-50"
        >
          Registrieren
        </button>
      </form>
    );
  }
  ```
  Create `frontend/src/app/(auth)/register/page.tsx`:
  ```tsx
  import { RegisterForm } from "@/features/auth/components/RegisterForm";
  export default function RegisterPage() {
    return <RegisterForm />;
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/features/auth/components/RegisterForm.test.tsx`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add "frontend/src/app/(auth)/register/page.tsx" frontend/src/features/auth/hooks/useRegister.ts frontend/src/features/auth/components/RegisterForm.tsx frontend/src/features/auth/components/RegisterForm.test.tsx
  git commit -m "feat(auth-ui): add RegisterForm with 12-char min and strength meter"
  ```

### Task 8.6: Verify-email page reads ?token= and calls backend

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/app/(auth)/verify-email/page.test.tsx`:
  ```tsx
  import { describe, it, expect, vi, afterEach } from "vitest";
  import { render, screen, waitFor } from "@testing-library/react";
  import VerifyEmailPage from "./page";

  vi.mock("next/navigation", () => ({
    useSearchParams: () => new URLSearchParams("?token=abc123"),
  }));

  describe("VerifyEmailPage", () => {
    afterEach(() => vi.restoreAllMocks());

    it("calls /api/auth/verify-email with token and shows success", async () => {
      const spy = vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify({ ok: true }), { status: 200 }),
      );
      render(<VerifyEmailPage />);
      await waitFor(() =>
        expect(screen.getByText(/email.*bestätigt/i)).toBeInTheDocument(),
      );
      const call = spy.mock.calls[0];
      expect(call[0]).toBe("/api/auth/verify-email");
      expect(JSON.parse((call[1] as RequestInit).body as string)).toEqual({
        token: "abc123",
      });
    });

    it("shows error message on 400", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify({ detail: "invalid" }), { status: 400 }),
      );
      render(<VerifyEmailPage />);
      await waitFor(() =>
        expect(screen.getByRole("alert")).toBeInTheDocument(),
      );
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- "src/app/(auth)/verify-email/page.test.tsx"`
  Expected: FAIL with `Cannot find module './page'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/app/(auth)/verify-email/page.tsx`:
  ```tsx
  "use client";

  import { useEffect, useState } from "react";
  import { useSearchParams } from "next/navigation";
  import Link from "next/link";
  import { authApi } from "@/features/auth/api";

  export default function VerifyEmailPage() {
    const params = useSearchParams();
    const token = params.get("token");
    const [state, setState] = useState<"pending" | "ok" | "error">("pending");

    useEffect(() => {
      if (!token) {
        setState("error");
        return;
      }
      authApi
        .verifyEmail(token)
        .then(() => setState("ok"))
        .catch(() => setState("error"));
    }, [token]);

    if (state === "pending") {
      return <p className="text-sm">Bestätige Email-Adresse…</p>;
    }

    if (state === "ok") {
      return (
        <div className="space-y-4">
          <h1 className="text-2xl font-semibold">Email bestätigt</h1>
          <p className="text-sm">Sie können sich jetzt anmelden.</p>
          <Link
            href="/login"
            className="block text-center rounded bg-blue-600 text-white py-2"
          >
            Zur Anmeldung
          </Link>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Bestätigung fehlgeschlagen</h1>
        <p role="alert" className="text-sm text-red-600">
          Der Bestätigungslink ist ungültig oder abgelaufen.
        </p>
        <Link href="/login" className="text-sm text-blue-600 hover:underline">
          Zur Anmeldung
        </Link>
      </div>
    );
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- "src/app/(auth)/verify-email/page.test.tsx"`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add "frontend/src/app/(auth)/verify-email/page.tsx" "frontend/src/app/(auth)/verify-email/page.test.tsx"
  git commit -m "feat(auth-ui): add verify-email page with token query param"
  ```

### Task 8.7: Forgot-password and reset-password pages

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/app/(auth)/forgot-password/page.test.tsx`:
  ```tsx
  import { describe, it, expect, vi, afterEach } from "vitest";
  import { render, screen, fireEvent, waitFor } from "@testing-library/react";
  import ForgotPasswordPage from "./page";

  describe("ForgotPasswordPage", () => {
    afterEach(() => vi.restoreAllMocks());

    it("shows generic success after submit regardless of email", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify({ message: "ok" }), { status: 200 }),
      );
      render(<ForgotPasswordPage />);
      fireEvent.change(screen.getByLabelText(/email/i), {
        target: { value: "any@x.z" },
      });
      fireEvent.click(screen.getByRole("button", { name: /senden/i }));
      await waitFor(() =>
        expect(screen.getByText(/wenn.*konto.*existiert/i)).toBeInTheDocument(),
      );
    });
  });
  ```
  Create `frontend/src/app/(auth)/reset-password/page.test.tsx`:
  ```tsx
  import { describe, it, expect, vi, afterEach } from "vitest";
  import { render, screen, fireEvent } from "@testing-library/react";
  import ResetPasswordPage from "./page";

  vi.mock("next/navigation", () => ({
    useSearchParams: () => new URLSearchParams("?token=r1"),
  }));

  describe("ResetPasswordPage", () => {
    afterEach(() => vi.restoreAllMocks());

    it("requires password confirmation to match", () => {
      render(<ResetPasswordPage />);
      fireEvent.change(screen.getByLabelText(/neues passwort$/i), {
        target: { value: "pw1234567890" },
      });
      fireEvent.change(screen.getByLabelText(/passwort bestätigen/i), {
        target: { value: "different12345" },
      });
      const btn = screen.getByRole("button", { name: /zurücksetzen/i });
      expect(btn).toBeDisabled();
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- "src/app/(auth)/forgot-password/page.test.tsx" "src/app/(auth)/reset-password/page.test.tsx"`
  Expected: FAIL — `Cannot find module './page'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/app/(auth)/forgot-password/page.tsx`:
  ```tsx
  "use client";

  import { useState } from "react";
  import { authApi } from "@/features/auth/api";

  export default function ForgotPasswordPage() {
    const [email, setEmail] = useState("");
    const [sent, setSent] = useState(false);
    const [loading, setLoading] = useState(false);

    async function onSubmit(e: React.FormEvent) {
      e.preventDefault();
      setLoading(true);
      await authApi.requestPasswordReset(email).catch(() => {});
      setLoading(false);
      setSent(true);
    }

    if (sent) {
      return (
        <div className="space-y-4">
          <h1 className="text-2xl font-semibold">Email versendet</h1>
          <p className="text-sm">
            Wenn ein Konto mit dieser Email existiert, haben wir einen
            Zurücksetzen-Link gesendet.
          </p>
        </div>
      );
    }

    return (
      <form className="space-y-4" onSubmit={onSubmit}>
        <h1 className="text-2xl font-semibold mb-6">Passwort vergessen</h1>
        <label className="block">
          <span className="text-sm font-medium">Email</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-blue-600 text-white py-2 disabled:opacity-50"
        >
          Link senden
        </button>
      </form>
    );
  }
  ```
  Create `frontend/src/app/(auth)/reset-password/page.tsx`:
  ```tsx
  "use client";

  import { useState } from "react";
  import { useSearchParams } from "next/navigation";
  import Link from "next/link";
  import { authApi } from "@/features/auth/api";
  import { PasswordStrengthMeter } from "@/features/auth/components/PasswordStrengthMeter";

  export default function ResetPasswordPage() {
    const params = useSearchParams();
    const token = params.get("token") ?? "";
    const [pw1, setPw1] = useState("");
    const [pw2, setPw2] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [done, setDone] = useState(false);

    const valid = pw1.length >= 12 && pw1 === pw2 && token;

    async function onSubmit(e: React.FormEvent) {
      e.preventDefault();
      if (!valid) return;
      setLoading(true);
      setError(null);
      try {
        await authApi.confirmPasswordReset(token, pw1);
        setDone(true);
      } catch {
        setError("Der Link ist ungültig oder abgelaufen.");
      } finally {
        setLoading(false);
      }
    }

    if (done) {
      return (
        <div className="space-y-4">
          <h1 className="text-2xl font-semibold">Passwort geändert</h1>
          <Link
            href="/login"
            className="block text-center rounded bg-blue-600 text-white py-2"
          >
            Zur Anmeldung
          </Link>
        </div>
      );
    }

    return (
      <form className="space-y-4" onSubmit={onSubmit}>
        <h1 className="text-2xl font-semibold mb-6">Neues Passwort setzen</h1>
        <label className="block">
          <span className="text-sm font-medium">Neues Passwort</span>
          <input
            type="password"
            autoComplete="new-password"
            required
            value={pw1}
            onChange={(e) => setPw1(e.target.value)}
            className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
          />
          <PasswordStrengthMeter password={pw1} />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Passwort bestätigen</span>
          <input
            type="password"
            autoComplete="new-password"
            required
            value={pw2}
            onChange={(e) => setPw2(e.target.value)}
            className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
          />
        </label>
        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={loading || !valid}
          className="w-full rounded bg-blue-600 text-white py-2 disabled:opacity-50"
        >
          Passwort zurücksetzen
        </button>
      </form>
    );
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- "src/app/(auth)/forgot-password/page.test.tsx" "src/app/(auth)/reset-password/page.test.tsx"`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add "frontend/src/app/(auth)/forgot-password" "frontend/src/app/(auth)/reset-password"
  git commit -m "feat(auth-ui): add forgot-password and reset-password pages"
  ```

### Task 8.8: Opus Gate 8A — UX Enumeration Sweep

- [ ] **Step 1: Invoke Opus reviewer**
  ```
  Agent({
    subagent_type: "general-purpose",
    model: "opus",
    description: "Opus UX review: enumeration + generic error messages",
    prompt: "Review all five auth pages and their forms for user-enumeration leaks. Files: frontend/src/app/(auth)/login/page.tsx, frontend/src/features/auth/components/LoginForm.tsx, frontend/src/features/auth/hooks/useLogin.ts, frontend/src/app/(auth)/register/page.tsx, frontend/src/features/auth/components/RegisterForm.tsx, frontend/src/features/auth/hooks/useRegister.ts, frontend/src/app/(auth)/verify-email/page.tsx, frontend/src/app/(auth)/forgot-password/page.tsx, frontend/src/app/(auth)/reset-password/page.tsx. For each user-visible error message, confirm: (1) Login errors never distinguish wrong-email from wrong-password — always 'Email oder Passwort ist falsch'. (2) Login errors never leak 'email not verified' as a distinct message (the spec allows a resend-verification affordance but it must not be triggered by a different error text). (3) Register form never confirms or denies whether an email already exists — always 'Check your email'. (4) Forgot-password form always shows the same generic success message regardless of whether the account exists. (5) Rate-limit (429) and locked (423) responses are either mapped to the same generic message or explicitly documented as acceptable deviations. (6) 2FA failure shows a generic 'Code ungültig' without revealing whether the challenge_id is expired vs the code is wrong. Also verify: no console.error with raw backend detail leaks PII, no error message contains the submitted email back to the user in a way that confirms it, and all form validation is client-side hints only — the server remains authoritative on the 12-char password rule. Report findings as file:line:issue."
  })
  ```
- [ ] **Step 2: Address any findings**
  Fix each reported issue with a new TDD cycle (failing test → fix → pass → commit with `fix(auth-ui):` scope).

---

## Phase 9: Settings/Security + Admin/Audit UI

**Goal:** Build `/settings/security` (password change, 2FA setup/disable, active sessions list) and `/admin/audit` (paginated audit viewer).

**Files:**
- Create: `frontend/src/app/settings/security/page.tsx`
- Create: `frontend/src/app/admin/audit/page.tsx`
- Create: `frontend/src/features/auth/components/PasswordChangeForm.tsx`
- Create: `frontend/src/features/auth/components/PasswordChangeForm.test.tsx`
- Create: `frontend/src/features/auth/components/TwoFactorSetup.tsx`
- Create: `frontend/src/features/auth/components/TwoFactorSetup.test.tsx`
- Create: `frontend/src/features/auth/components/TwoFactorDisable.tsx`
- Create: `frontend/src/features/auth/components/TwoFactorDisable.test.tsx`
- Create: `frontend/src/features/auth/components/ActiveSessionsList.tsx`
- Create: `frontend/src/features/auth/components/ActiveSessionsList.test.tsx`
- Create: `frontend/src/features/auth/components/AuditLogTable.tsx`
- Create: `frontend/src/features/auth/components/AuditLogTable.test.tsx`
- Create: `frontend/src/features/auth/hooks/useActiveSessions.ts`
- Create: `frontend/src/features/auth/hooks/useAuditLog.ts`
- Modify: `frontend/package.json`

### Task 9.1: Install qrcode.react and scaffold settings page

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/app/settings/security/page.test.tsx`:
  ```tsx
  import { describe, it, expect } from "vitest";
  import { render, screen } from "@testing-library/react";
  import SecurityPage from "./page";

  describe("SecurityPage", () => {
    it("renders password, 2fa, and sessions section headings", () => {
      render(<SecurityPage />);
      expect(
        screen.getByRole("heading", { name: /passwort ändern/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { name: /zwei-faktor/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { name: /aktive sitzungen/i }),
      ).toBeInTheDocument();
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/app/settings/security/page.test.tsx`
  Expected: FAIL with `Cannot find module './page'`.
- [ ] **Step 3: Implement**
  Install dep:
  ```bash
  cd frontend && npm install qrcode.react
  ```
  Create `frontend/src/app/settings/security/page.tsx` (stub wiring the three cards):
  ```tsx
  "use client";

  import { PasswordChangeForm } from "@/features/auth/components/PasswordChangeForm";
  import { TwoFactorSetup } from "@/features/auth/components/TwoFactorSetup";
  import { ActiveSessionsList } from "@/features/auth/components/ActiveSessionsList";

  export default function SecurityPage() {
    return (
      <div className="max-w-2xl mx-auto p-6 space-y-10">
        <section>
          <h2 className="text-xl font-semibold mb-4">Passwort ändern</h2>
          <PasswordChangeForm />
        </section>
        <section>
          <h2 className="text-xl font-semibold mb-4">Zwei-Faktor-Authentifizierung</h2>
          <TwoFactorSetup />
        </section>
        <section>
          <h2 className="text-xl font-semibold mb-4">Aktive Sitzungen</h2>
          <ActiveSessionsList />
        </section>
      </div>
    );
  }
  ```
  Create stub components so the page compiles — each will get filled in by the following tasks:
  ```tsx
  // frontend/src/features/auth/components/PasswordChangeForm.tsx
  "use client";
  export function PasswordChangeForm() {
    return <div data-testid="password-change-form" />;
  }
  ```
  ```tsx
  // frontend/src/features/auth/components/TwoFactorSetup.tsx
  "use client";
  export function TwoFactorSetup() {
    return <div data-testid="two-factor-setup" />;
  }
  ```
  ```tsx
  // frontend/src/features/auth/components/ActiveSessionsList.tsx
  "use client";
  export function ActiveSessionsList() {
    return <div data-testid="active-sessions-list" />;
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/app/settings/security/page.test.tsx`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/package.json frontend/package-lock.json frontend/src/app/settings/security frontend/src/features/auth/components/PasswordChangeForm.tsx frontend/src/features/auth/components/TwoFactorSetup.tsx frontend/src/features/auth/components/ActiveSessionsList.tsx
  git commit -m "feat(auth-ui): scaffold /settings/security page with three section stubs"
  ```

### Task 9.2: PasswordChangeForm

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/features/auth/components/PasswordChangeForm.test.tsx`:
  ```tsx
  import { describe, it, expect, vi, afterEach } from "vitest";
  import { render, screen, fireEvent, waitFor } from "@testing-library/react";
  import { PasswordChangeForm } from "./PasswordChangeForm";

  describe("PasswordChangeForm", () => {
    afterEach(() => vi.restoreAllMocks());

    it("requires current password field", () => {
      render(<PasswordChangeForm />);
      const current = screen.getByLabelText(/aktuelles passwort/i);
      expect(current).toBeRequired();
    });

    it("disables submit if new password < 12 chars", () => {
      render(<PasswordChangeForm />);
      fireEvent.change(screen.getByLabelText(/aktuelles passwort/i), {
        target: { value: "oldpw1234567890" },
      });
      fireEvent.change(screen.getByLabelText(/neues passwort$/i), {
        target: { value: "short" },
      });
      const btn = screen.getByRole("button", { name: /ändern/i });
      expect(btn).toBeDisabled();
    });

    it("submits and shows success", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify({ ok: true }), { status: 200 }),
      );
      render(<PasswordChangeForm />);
      fireEvent.change(screen.getByLabelText(/aktuelles passwort/i), {
        target: { value: "oldpw1234567890" },
      });
      fireEvent.change(screen.getByLabelText(/neues passwort$/i), {
        target: { value: "newpw1234567890" },
      });
      fireEvent.click(screen.getByRole("button", { name: /ändern/i }));
      await waitFor(() =>
        expect(screen.getByText(/passwort geändert/i)).toBeInTheDocument(),
      );
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/features/auth/components/PasswordChangeForm.test.tsx`
  Expected: FAIL — the stub does not render required fields.
- [ ] **Step 3: Implement**
  Replace `frontend/src/features/auth/components/PasswordChangeForm.tsx`:
  ```tsx
  "use client";

  import { useState } from "react";
  import { authApi } from "@/features/auth/api";

  export function PasswordChangeForm() {
    const [current, setCurrent] = useState("");
    const [next, setNext] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [done, setDone] = useState(false);

    const valid = next.length >= 12;

    async function onSubmit(e: React.FormEvent) {
      e.preventDefault();
      if (!valid) return;
      setLoading(true);
      setError(null);
      try {
        await authApi.changePassword(current, next);
        setDone(true);
        setCurrent("");
        setNext("");
      } catch {
        setError("Änderung fehlgeschlagen.");
      } finally {
        setLoading(false);
      }
    }

    return (
      <form className="space-y-4" onSubmit={onSubmit}>
        <label className="block">
          <span className="text-sm font-medium">Aktuelles Passwort</span>
          <input
            type="password"
            autoComplete="current-password"
            required
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Neues Passwort</span>
          <input
            type="password"
            autoComplete="new-password"
            required
            minLength={12}
            value={next}
            onChange={(e) => setNext(e.target.value)}
            className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
          />
        </label>
        {done && <p className="text-sm text-green-600">Passwort geändert.</p>}
        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={loading || !valid}
          className="rounded bg-blue-600 text-white px-4 py-2 disabled:opacity-50"
        >
          Passwort ändern
        </button>
      </form>
    );
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/features/auth/components/PasswordChangeForm.test.tsx`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/features/auth/components/PasswordChangeForm.tsx frontend/src/features/auth/components/PasswordChangeForm.test.tsx
  git commit -m "feat(auth-ui): implement PasswordChangeForm with current+new password"
  ```

### Task 9.3: TwoFactorSetup with QR code

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/features/auth/components/TwoFactorSetup.test.tsx`:
  ```tsx
  import { describe, it, expect, vi, afterEach } from "vitest";
  import { render, screen, fireEvent, waitFor } from "@testing-library/react";
  import { TwoFactorSetup } from "./TwoFactorSetup";

  describe("TwoFactorSetup", () => {
    afterEach(() => vi.restoreAllMocks());

    it("fetches and renders QR + secret fallback", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(
          JSON.stringify({
            secret: "JBSWY3DPEHPK3PXP",
            provisioning_uri:
              "otpauth://totp/LRA:a@b.c?secret=JBSWY3DPEHPK3PXP&issuer=LRA",
          }),
          { status: 200 },
        ),
      );
      render(<TwoFactorSetup />);
      fireEvent.click(screen.getByRole("button", { name: /2fa einrichten/i }));
      await waitFor(() =>
        expect(screen.getByText(/JBSWY3DPEHPK3PXP/)).toBeInTheDocument(),
      );
      expect(screen.getByTestId("totp-qr")).toBeInTheDocument();
    });

    it("requires 6-digit code to enable", async () => {
      vi.spyOn(global, "fetch").mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            secret: "X",
            provisioning_uri: "otpauth://totp/LRA:a@b.c?secret=X",
          }),
          { status: 200 },
        ),
      );
      render(<TwoFactorSetup />);
      fireEvent.click(screen.getByRole("button", { name: /2fa einrichten/i }));
      await screen.findByTestId("totp-qr");
      const btn = screen.getByRole("button", { name: /aktivieren/i });
      expect(btn).toBeDisabled();
      fireEvent.change(screen.getByLabelText(/6-stelliger code/i), {
        target: { value: "12345" },
      });
      expect(btn).toBeDisabled();
      fireEvent.change(screen.getByLabelText(/6-stelliger code/i), {
        target: { value: "123456" },
      });
      expect(btn).not.toBeDisabled();
    });

    it("shows success after enable", async () => {
      const spy = vi.spyOn(global, "fetch");
      spy.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            secret: "X",
            provisioning_uri: "otpauth://totp/LRA:a@b.c?secret=X",
          }),
          { status: 200 },
        ),
      );
      spy.mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), { status: 200 }),
      );
      render(<TwoFactorSetup />);
      fireEvent.click(screen.getByRole("button", { name: /2fa einrichten/i }));
      await screen.findByTestId("totp-qr");
      fireEvent.change(screen.getByLabelText(/6-stelliger code/i), {
        target: { value: "123456" },
      });
      fireEvent.click(screen.getByRole("button", { name: /aktivieren/i }));
      await waitFor(() =>
        expect(screen.getByText(/2fa aktiviert/i)).toBeInTheDocument(),
      );
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/features/auth/components/TwoFactorSetup.test.tsx`
  Expected: FAIL — stub has no button.
- [ ] **Step 3: Implement**
  Replace `frontend/src/features/auth/components/TwoFactorSetup.tsx`:
  ```tsx
  "use client";

  import { useState } from "react";
  import { QRCodeSVG } from "qrcode.react";

  interface SetupPayload {
    secret: string;
    provisioning_uri: string;
  }

  export function TwoFactorSetup() {
    const [setup, setSetup] = useState<SetupPayload | null>(null);
    const [code, setCode] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [done, setDone] = useState(false);

    async function startSetup() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch("/api/auth/2fa/setup", {
          method: "POST",
          credentials: "include",
        });
        if (!res.ok) throw new Error();
        setSetup(await res.json());
      } catch {
        setError("Einrichtung konnte nicht gestartet werden.");
      } finally {
        setLoading(false);
      }
    }

    async function enable() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch("/api/auth/2fa/enable", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code }),
        });
        if (!res.ok) throw new Error();
        setDone(true);
      } catch {
        setError("Code ist ungültig.");
      } finally {
        setLoading(false);
      }
    }

    if (done) {
      return (
        <p className="text-sm text-green-600">
          2FA aktiviert. Sie wurden von allen anderen Sitzungen abgemeldet.
        </p>
      );
    }

    if (!setup) {
      return (
        <button
          type="button"
          onClick={startSetup}
          disabled={loading}
          className="rounded bg-blue-600 text-white px-4 py-2 disabled:opacity-50"
        >
          2FA einrichten
        </button>
      );
    }

    const valid = /^\d{6}$/.test(code);

    return (
      <div className="space-y-4">
        <div
          data-testid="totp-qr"
          className="inline-block bg-white p-3 rounded border"
        >
          <QRCodeSVG value={setup.provisioning_uri} size={160} />
        </div>
        <p className="text-xs text-neutral-600 dark:text-neutral-400">
          Können Sie den QR-Code nicht scannen? Geben Sie den folgenden Schlüssel
          manuell in Ihre Authenticator-App ein:
        </p>
        <code className="block font-mono text-sm bg-neutral-100 dark:bg-neutral-800 p-2 rounded">
          {setup.secret}
        </code>
        <label className="block">
          <span className="text-sm font-medium">6-stelliger Code</span>
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900 tracking-widest text-center"
          />
        </label>
        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}
        <button
          type="button"
          onClick={enable}
          disabled={!valid || loading}
          className="rounded bg-blue-600 text-white px-4 py-2 disabled:opacity-50"
        >
          Aktivieren
        </button>
      </div>
    );
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/features/auth/components/TwoFactorSetup.test.tsx`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/features/auth/components/TwoFactorSetup.tsx frontend/src/features/auth/components/TwoFactorSetup.test.tsx
  git commit -m "feat(auth-ui): implement TwoFactorSetup with QR + manual secret fallback"
  ```

### Task 9.4: TwoFactorDisable

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/features/auth/components/TwoFactorDisable.test.tsx`:
  ```tsx
  import { describe, it, expect, vi, afterEach } from "vitest";
  import { render, screen, fireEvent } from "@testing-library/react";
  import { TwoFactorDisable } from "./TwoFactorDisable";

  describe("TwoFactorDisable", () => {
    afterEach(() => vi.restoreAllMocks());

    it("requires both password and 6-digit code", () => {
      render(<TwoFactorDisable />);
      const btn = screen.getByRole("button", { name: /deaktivieren/i });
      expect(btn).toBeDisabled();
      fireEvent.change(screen.getByLabelText(/aktuelles passwort/i), {
        target: { value: "pw1234567890" },
      });
      expect(btn).toBeDisabled();
      fireEvent.change(screen.getByLabelText(/6-stelliger code/i), {
        target: { value: "123456" },
      });
      expect(btn).not.toBeDisabled();
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/features/auth/components/TwoFactorDisable.test.tsx`
  Expected: FAIL with `Cannot find module './TwoFactorDisable'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/features/auth/components/TwoFactorDisable.tsx`:
  ```tsx
  "use client";

  import { useState } from "react";

  export function TwoFactorDisable() {
    const [password, setPassword] = useState("");
    const [code, setCode] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const valid = password.length > 0 && /^\d{6}$/.test(code);

    async function onSubmit(e: React.FormEvent) {
      e.preventDefault();
      if (!valid) return;
      setLoading(true);
      setError(null);
      try {
        const res = await fetch("/api/auth/2fa/disable", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ current_password: password, code }),
        });
        if (!res.ok) throw new Error();
      } catch {
        setError("Deaktivierung fehlgeschlagen.");
      } finally {
        setLoading(false);
      }
    }

    return (
      <form className="space-y-4" onSubmit={onSubmit}>
        <label className="block">
          <span className="text-sm font-medium">Aktuelles Passwort</span>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900"
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium">6-stelliger Code</span>
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            className="mt-1 block w-full rounded border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900 tracking-widest text-center"
          />
        </label>
        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={!valid || loading}
          className="rounded bg-red-600 text-white px-4 py-2 disabled:opacity-50"
        >
          2FA deaktivieren
        </button>
      </form>
    );
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/features/auth/components/TwoFactorDisable.test.tsx`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/features/auth/components/TwoFactorDisable.tsx frontend/src/features/auth/components/TwoFactorDisable.test.tsx
  git commit -m "feat(auth-ui): add TwoFactorDisable component requiring password+code"
  ```

### Task 9.5: ActiveSessionsList with revoke

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/features/auth/components/ActiveSessionsList.test.tsx`:
  ```tsx
  import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
  import { render, screen, fireEvent, waitFor } from "@testing-library/react";
  import { ActiveSessionsList } from "./ActiveSessionsList";

  const sessions = [
    {
      id: "s1",
      user_agent: "Chrome",
      ip_address: "1.2.3.4",
      created_at: "2026-04-13T10:00:00Z",
      last_used_at: "2026-04-13T11:00:00Z",
      expires_at: "2026-04-20T00:00:00Z",
      is_current: true,
    },
    {
      id: "s2",
      user_agent: "Firefox",
      ip_address: "5.6.7.8",
      created_at: "2026-04-12T10:00:00Z",
      last_used_at: "2026-04-12T11:00:00Z",
      expires_at: "2026-04-19T00:00:00Z",
      is_current: false,
    },
  ];

  describe("ActiveSessionsList", () => {
    beforeEach(() => {
      Object.defineProperty(window, "location", {
        value: { href: "" },
        writable: true,
      });
    });
    afterEach(() => vi.restoreAllMocks());

    it("marks current session with a badge", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify(sessions), { status: 200 }),
      );
      render(<ActiveSessionsList />);
      await screen.findByText("Chrome");
      expect(screen.getByText(/dieses gerät/i)).toBeInTheDocument();
    });

    it("revoking a non-current session removes the row", async () => {
      const spy = vi.spyOn(global, "fetch");
      spy.mockResolvedValueOnce(
        new Response(JSON.stringify(sessions), { status: 200 }),
      );
      spy.mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), { status: 200 }),
      );
      render(<ActiveSessionsList />);
      await screen.findByText("Firefox");
      const revokeBtns = screen.getAllByRole("button", { name: /widerrufen/i });
      fireEvent.click(revokeBtns[1]);
      await waitFor(() =>
        expect(screen.queryByText("Firefox")).not.toBeInTheDocument(),
      );
    });

    it("revoking current session redirects to /login", async () => {
      const spy = vi.spyOn(global, "fetch");
      spy.mockResolvedValueOnce(
        new Response(JSON.stringify(sessions), { status: 200 }),
      );
      spy.mockResolvedValueOnce(
        new Response(JSON.stringify({ current_session_revoked: true }), {
          status: 200,
        }),
      );
      render(<ActiveSessionsList />);
      await screen.findByText("Chrome");
      const revokeBtns = screen.getAllByRole("button", { name: /widerrufen/i });
      fireEvent.click(revokeBtns[0]);
      await waitFor(() => expect(window.location.href).toBe("/login"));
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/features/auth/components/ActiveSessionsList.test.tsx`
  Expected: FAIL — stub has no list.
- [ ] **Step 3: Implement**
  Create `frontend/src/features/auth/hooks/useActiveSessions.ts`:
  ```ts
  "use client";
  import { useCallback, useEffect, useState } from "react";

  export interface ActiveSession {
    id: string;
    user_agent: string | null;
    ip_address: string | null;
    created_at: string;
    last_used_at: string;
    expires_at: string;
    is_current: boolean;
  }

  export function useActiveSessions() {
    const [sessions, setSessions] = useState<ActiveSession[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
      setLoading(true);
      try {
        const res = await fetch("/api/auth/sessions", { credentials: "include" });
        if (!res.ok) throw new Error();
        setSessions(await res.json());
      } catch {
        setError("Sitzungen konnten nicht geladen werden.");
      } finally {
        setLoading(false);
      }
    }, []);

    useEffect(() => {
      void load();
    }, [load]);

    async function revoke(
      id: string,
    ): Promise<{ current_session_revoked?: boolean }> {
      const res = await fetch(`/api/auth/sessions/${id}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) throw new Error("revoke failed");
      const body = await res.json().catch(() => ({}));
      if (!body.current_session_revoked) {
        setSessions((s) => s.filter((x) => x.id !== id));
      }
      return body;
    }

    return { sessions, loading, error, revoke };
  }
  ```
  Replace `frontend/src/features/auth/components/ActiveSessionsList.tsx`:
  ```tsx
  "use client";

  import { useActiveSessions } from "../hooks/useActiveSessions";

  export function ActiveSessionsList() {
    const { sessions, loading, error, revoke } = useActiveSessions();

    async function onRevoke(id: string) {
      const res = await revoke(id);
      if (res.current_session_revoked) {
        window.location.href = "/login";
      }
    }

    if (loading) return <p className="text-sm">Lädt…</p>;
    if (error)
      return (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      );

    return (
      <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
        {sessions.map((s) => (
          <li
            key={s.id}
            className="py-3 flex items-center justify-between gap-4"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium truncate">
                  {s.user_agent ?? "Unbekanntes Gerät"}
                </span>
                {s.is_current && (
                  <span className="text-xs rounded bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 px-2 py-0.5">
                    Dieses Gerät
                  </span>
                )}
              </div>
              <div className="text-xs text-neutral-500 dark:text-neutral-400">
                {s.ip_address ?? "—"} · zuletzt aktiv{" "}
                {new Date(s.last_used_at).toLocaleString("de-DE")}
              </div>
            </div>
            <button
              type="button"
              onClick={() => onRevoke(s.id)}
              className="text-sm text-red-600 hover:underline"
            >
              Widerrufen
            </button>
          </li>
        ))}
      </ul>
    );
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/features/auth/components/ActiveSessionsList.test.tsx`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/features/auth/hooks/useActiveSessions.ts frontend/src/features/auth/components/ActiveSessionsList.tsx frontend/src/features/auth/components/ActiveSessionsList.test.tsx
  git commit -m "feat(auth-ui): implement ActiveSessionsList with revoke"
  ```

### Task 9.6: AuditLogTable and /admin/audit page

- [ ] **Step 1: Write the failing test**
  Create `frontend/src/features/auth/components/AuditLogTable.test.tsx`:
  ```tsx
  import { describe, it, expect, vi, afterEach } from "vitest";
  import { render, screen, fireEvent, waitFor } from "@testing-library/react";
  import { AuditLogTable } from "./AuditLogTable";

  const page1 = {
    items: [
      {
        id: "a1",
        user_id: "u1",
        event: "login.success",
        ip_address: "1.2.3.4",
        user_agent: "UA",
        metadata: {},
        created_at: "2026-04-13T10:00:00Z",
      },
    ],
    total: 2,
  };

  describe("AuditLogTable", () => {
    afterEach(() => vi.restoreAllMocks());

    it("renders empty state when no items", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify({ items: [], total: 0 }), { status: 200 }),
      );
      render(<AuditLogTable />);
      await waitFor(() =>
        expect(screen.getByText(/keine einträge/i)).toBeInTheDocument(),
      );
    });

    it("filters by event", async () => {
      const spy = vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify(page1), { status: 200 }),
      );
      render(<AuditLogTable />);
      await screen.findByText("login.success");
      fireEvent.change(screen.getByLabelText(/event/i), {
        target: { value: "logout" },
      });
      fireEvent.click(screen.getByRole("button", { name: /filter/i }));
      await waitFor(() => {
        const last = spy.mock.calls.at(-1);
        expect((last?.[0] as string) ?? "").toContain("event=logout");
      });
    });

    it("paginates by offset", async () => {
      const spy = vi.spyOn(global, "fetch").mockResolvedValue(
        new Response(JSON.stringify(page1), { status: 200 }),
      );
      render(<AuditLogTable />);
      await screen.findByText("login.success");
      fireEvent.click(screen.getByRole("button", { name: /weiter/i }));
      await waitFor(() => {
        const last = spy.mock.calls.at(-1);
        expect((last?.[0] as string) ?? "").toContain("offset=50");
      });
    });
  });
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd frontend && npm test -- src/features/auth/components/AuditLogTable.test.tsx`
  Expected: FAIL with `Cannot find module './AuditLogTable'`.
- [ ] **Step 3: Implement**
  Create `frontend/src/features/auth/hooks/useAuditLog.ts`:
  ```ts
  "use client";
  import { useCallback, useEffect, useState } from "react";

  export interface AuditEntry {
    id: string;
    user_id: string | null;
    event: string;
    ip_address: string | null;
    user_agent: string | null;
    metadata: Record<string, unknown>;
    created_at: string;
  }

  export interface AuditPage {
    items: AuditEntry[];
    total: number;
  }

  interface Params {
    event: string;
    user_id: string;
    offset: number;
    limit: number;
  }

  export function useAuditLog(initial: Partial<Params> = {}) {
    const [params, setParams] = useState<Params>({
      event: "",
      user_id: "",
      offset: 0,
      limit: 50,
      ...initial,
    });
    const [data, setData] = useState<AuditPage>({ items: [], total: 0 });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
      setLoading(true);
      setError(null);
      const qs = new URLSearchParams();
      if (params.event) qs.set("event", params.event);
      if (params.user_id) qs.set("user_id", params.user_id);
      qs.set("limit", String(params.limit));
      qs.set("offset", String(params.offset));
      try {
        const res = await fetch(`/api/admin/audit?${qs.toString()}`, {
          credentials: "include",
        });
        if (!res.ok) throw new Error();
        setData(await res.json());
      } catch {
        setError("Audit-Log konnte nicht geladen werden.");
      } finally {
        setLoading(false);
      }
    }, [params]);

    useEffect(() => {
      void load();
    }, [load]);

    return { data, params, setParams, loading, error, reload: load };
  }
  ```
  Create `frontend/src/features/auth/components/AuditLogTable.tsx`:
  ```tsx
  "use client";

  import { useState } from "react";
  import { useAuditLog } from "../hooks/useAuditLog";

  const EVENTS = [
    "",
    "user.register",
    "user.email_verified",
    "login.success",
    "login.fail",
    "login.2fa_required",
    "login.2fa_success",
    "login.2fa_fail",
    "logout",
    "session.revoke",
    "session.refresh_reuse_detected",
    "password.change",
    "password.reset_requested",
    "password.reset_completed",
    "2fa.enable",
    "2fa.disable",
    "admin.user_lock",
    "admin.user_unlock",
    "admin.2fa_disable",
  ];

  export function AuditLogTable() {
    const { data, params, setParams, loading, error } = useAuditLog();
    const [eventFilter, setEventFilter] = useState("");
    const [userFilter, setUserFilter] = useState("");

    function applyFilter() {
      setParams({ ...params, event: eventFilter, user_id: userFilter, offset: 0 });
    }

    function nextPage() {
      setParams({ ...params, offset: params.offset + params.limit });
    }
    function prevPage() {
      setParams({ ...params, offset: Math.max(0, params.offset - params.limit) });
    }

    return (
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2 items-end">
          <label className="flex flex-col">
            <span className="text-xs">Event</span>
            <select
              value={eventFilter}
              onChange={(e) => setEventFilter(e.target.value)}
              className="rounded border px-2 py-1 bg-white dark:bg-neutral-900"
            >
              {EVENTS.map((e) => (
                <option key={e} value={e}>
                  {e || "(alle)"}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col">
            <span className="text-xs">User-ID</span>
            <input
              type="text"
              value={userFilter}
              onChange={(e) => setUserFilter(e.target.value)}
              className="rounded border px-2 py-1 bg-white dark:bg-neutral-900"
            />
          </label>
          <button
            type="button"
            onClick={applyFilter}
            className="rounded bg-blue-600 text-white px-3 py-1"
          >
            Filter anwenden
          </button>
        </div>
        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}
        {loading && <p className="text-sm">Lädt…</p>}
        {!loading && data.items.length === 0 && (
          <p className="text-sm text-neutral-500">Keine Einträge.</p>
        )}
        {data.items.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b">
                <th className="py-2">Zeit</th>
                <th>Event</th>
                <th>User</th>
                <th>IP</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((row) => (
                <tr key={row.id} className="border-b last:border-0">
                  <td className="py-1">
                    {new Date(row.created_at).toLocaleString("de-DE")}
                  </td>
                  <td>{row.event}</td>
                  <td className="font-mono text-xs">{row.user_id ?? "—"}</td>
                  <td>{row.ip_address ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="flex gap-2 justify-end">
          <button
            type="button"
            onClick={prevPage}
            disabled={params.offset === 0}
            className="rounded border px-3 py-1 disabled:opacity-50"
          >
            Zurück
          </button>
          <button
            type="button"
            onClick={nextPage}
            disabled={params.offset + params.limit >= data.total}
            className="rounded border px-3 py-1 disabled:opacity-50"
          >
            Weiter
          </button>
        </div>
      </div>
    );
  }
  ```
  Create `frontend/src/app/admin/audit/page.tsx`:
  ```tsx
  "use client";

  import { useEffect } from "react";
  import { useRouter } from "next/navigation";
  import { useAuth } from "@/features/auth/hooks/useAuth";
  import { AuditLogTable } from "@/features/auth/components/AuditLogTable";

  export default function AdminAuditPage() {
    const { state } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (state.status === "authenticated" && state.user.role !== "admin") {
        router.replace("/");
      }
    }, [state, router]);

    if (state.status !== "authenticated" || state.user.role !== "admin") {
      return null;
    }

    return (
      <div className="max-w-4xl mx-auto p-6">
        <h1 className="text-2xl font-semibold mb-6">Audit-Log</h1>
        <AuditLogTable />
      </div>
    );
  }
  ```
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd frontend && npm test -- src/features/auth/components/AuditLogTable.test.tsx`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add frontend/src/features/auth/hooks/useAuditLog.ts frontend/src/features/auth/components/AuditLogTable.tsx frontend/src/features/auth/components/AuditLogTable.test.tsx frontend/src/app/admin/audit
  git commit -m "feat(auth-ui): add AuditLogTable and /admin/audit page with role gate"
  ```

---

## Phase 10: Polish & Deploy

**Goal:** Env-var hygiene, README updates, remove the old API_KEY middleware references, and a Vercel deploy checklist.

**Files:**
- Modify: `.env.example`
- Modify: `backend/main.py`
- Modify: `README.md`
- Modify: `frontend/src/lib/api.ts`
- Create: `backend/tests/test_env_hygiene.py`
- Create: `backend/tests/test_no_api_key_references.py`

### Task 10.1: .env.example lists all new vars

- [ ] **Step 1: Write the failing test**
  Create `backend/tests/test_env_hygiene.py`:
  ```python
  from pathlib import Path

  REQUIRED = [
      "JWT_SECRET",
      "SERVICE_TOKEN",
      "RESEND_API_KEY",
      "RESEND_FROM_EMAIL",
      "BACKEND_URL",
      "SESSION_ENCRYPTION_KEY",
  ]

  def test_env_example_lists_all_new_vars() -> None:
      root = Path(__file__).resolve().parents[2]
      content = (root / ".env.example").read_text()
      missing = [k for k in REQUIRED if k not in content]
      assert not missing, f"missing from .env.example: {missing}"
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_env_hygiene.py -x`
  Expected: FAIL — missing keys listed.
- [ ] **Step 3: Implement**
  Edit `.env.example` at repo root, ensuring each of the required vars appears exactly once. Example additions:
  ```
  # Auth
  JWT_SECRET=
  SERVICE_TOKEN=
  SESSION_ENCRYPTION_KEY=

  # Email (Resend)
  RESEND_API_KEY=
  RESEND_FROM_EMAIL=noreply@example.com

  # Frontend → backend proxy
  BACKEND_URL=http://localhost:8001
  ```
  Remove any legacy `API_KEY=` line.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_env_hygiene.py -x`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add .env.example backend/tests/test_env_hygiene.py
  git commit -m "chore(auth): list new auth env vars in .env.example"
  ```

### Task 10.2: Remove API_KEY references and dead middleware registration

- [ ] **Step 1: Write the failing test**
  Create `backend/tests/test_no_api_key_references.py`:
  ```python
  import re
  from pathlib import Path

  ALLOWED_FILES = {
      "backend/tests/test_no_api_key_references.py",
  }

  def test_no_api_key_references() -> None:
      root = Path(__file__).resolve().parents[2]
      pattern = re.compile(r"\bAPI_KEY\b")
      offenders: list[str] = []
      for path in root.rglob("*"):
          if not path.is_file():
              continue
          if any(part in {".git", "node_modules", ".next", "dist", ".venv"} for part in path.parts):
              continue
          rel = path.relative_to(root).as_posix()
          if rel in ALLOWED_FILES:
              continue
          if path.suffix not in {".py", ".ts", ".tsx", ".js", ".md", ".example"}:
              continue
          try:
              text = path.read_text(encoding="utf-8")
          except UnicodeDecodeError:
              continue
          if pattern.search(text):
              offenders.append(rel)
      assert not offenders, f"stale API_KEY references: {offenders}"
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_no_api_key_references.py -x`
  Expected: FAIL listing files still referencing `API_KEY`.
- [ ] **Step 3: Implement**
  - In `backend/main.py`, delete any `APIKeyAuthMiddleware` import and `app.add_middleware(APIKeyAuthMiddleware, ...)` call. Confirm only `ServiceTokenMiddleware` and `JWTAuthMiddleware` are registered (in that order after `CORSMiddleware`).
  - In `frontend/src/lib/api.ts`, remove any header such as `"X-API-Key": process.env.NEXT_PUBLIC_API_KEY` from `fetchApi`. All auth now flows through cookies via the Route Handlers.
  - Delete any remaining `API_KEY` references in Markdown (README fragments), keeping only the mention inside `test_no_api_key_references.py` itself.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_no_api_key_references.py -x`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add backend/main.py frontend/src/lib/api.ts backend/tests/test_no_api_key_references.py
  git commit -m "chore(auth): remove legacy API_KEY references and middleware wiring"
  ```

### Task 10.3: Middleware introspection test

- [ ] **Step 1: Write the failing test**
  Append to `backend/tests/test_env_hygiene.py` (or create `backend/tests/test_middleware_registration.py`):
  ```python
  from starlette.middleware.cors import CORSMiddleware
  from backend.main import app
  from backend.middleware.service_token import ServiceTokenMiddleware
  from backend.middleware.auth import JWTAuthMiddleware


  def test_main_registers_new_middleware_only() -> None:
      classes = [m.cls for m in app.user_middleware]
      assert CORSMiddleware in classes
      assert ServiceTokenMiddleware in classes
      assert JWTAuthMiddleware in classes
      for m in classes:
          assert m.__name__ != "APIKeyAuthMiddleware"
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_middleware_registration.py -x`
  Expected: FAIL if the module does not yet exist or registration is wrong.
- [ ] **Step 3: Implement**
  Ensure `backend/main.py` imports and registers `ServiceTokenMiddleware` and `JWTAuthMiddleware` in that order after `CORSMiddleware`, and does NOT import `APIKeyAuthMiddleware`.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_middleware_registration.py -x`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add backend/tests/test_middleware_registration.py backend/main.py
  git commit -m "test(auth): assert main.py registers ServiceToken + JWT middleware only"
  ```

### Task 10.4: README and Vercel deploy checklist

- [ ] **Step 1: Write the failing test**
  Create a lightweight README shape assertion as `backend/tests/test_readme_auth_section.py`:
  ```python
  from pathlib import Path

  def test_readme_mentions_new_auth_system() -> None:
      root = Path(__file__).resolve().parents[2]
      text = (root / "README.md").read_text(encoding="utf-8")
      for needle in ("JWT", "Resend", "BACKEND_URL", "2FA"):
          assert needle in text, f"README missing: {needle}"
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `cd backend && python -m pytest tests/test_readme_auth_section.py -x`
  Expected: FAIL.
- [ ] **Step 3: Implement**
  Update `README.md` with a new "Authentication" section that:
  - Describes the multi-user system (email+password, email verification, optional TOTP 2FA, password reset, active sessions dashboard, admin audit log).
  - Lists the new env vars (`JWT_SECRET`, `SERVICE_TOKEN`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `BACKEND_URL`, `SESSION_ENCRYPTION_KEY`).
  - Links to Resend domain verification at `https://resend.com/domains` with a note that it's a one-time human step.
  - Describes the Vercel deploy checklist:
    1. Set `BACKEND_URL` in the frontend service env to the deployed FastAPI service URL.
    2. Set `JWT_SECRET`, `SERVICE_TOKEN`, `SESSION_ENCRYPTION_KEY`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `DATABASE_URL`, `KV_REST_API_URL`, `KV_REST_API_TOKEN` in the backend service env.
    3. Run Alembic migrations against Neon: `alembic upgrade head`.
    4. Verify `vercel.json` `experimentalServices` still exposes both services and the `/api/*` rewrite carve-out is in place.
    5. Smoke-test: register a user via `/register`, check console-mode mail in backend logs (dev) or Resend dashboard (prod), verify email, log in, enable 2FA, log in again with 2FA.
- [ ] **Step 4: Run test to verify it passes**
  Run: `cd backend && python -m pytest tests/test_readme_auth_section.py -x`
  Expected: PASS.
- [ ] **Step 5: Commit**
  ```bash
  git add README.md backend/tests/test_readme_auth_section.py
  git commit -m "docs(auth): document multi-user auth system and Vercel deploy checklist"
  ```

### Task 10.5: Final full test run

- [ ] **Step 1: Run backend suite**
  Run: `cd backend && python -m pytest`
  Expected: all tests pass including the new auth and hygiene tests.
- [ ] **Step 2: Run frontend suite**
  Run: `cd frontend && npm test -- --run`
  Expected: all vitest suites pass.
- [ ] **Step 3: Lint and typecheck**
  Run: `cd backend && ruff check . && mypy .`
  Run: `cd frontend && npm run lint && npx tsc --noEmit`
  Expected: clean.
- [ ] **Step 4: Commit any fixups**
  If the above surfaces issues, fix them in small TDD cycles with `fix(auth-ui):` or `fix(auth):` scopes.
- [ ] **Step 5: Final commit**
  ```bash
  git commit --allow-empty -m "chore(auth): phase 10 polish complete"
  ```

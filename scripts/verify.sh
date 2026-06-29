#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
PYTEST_DB=""
ALEMBIC_DB=""

cleanup() {
  [[ -n "$PYTEST_DB" ]] && rm -f "$PYTEST_DB"
  [[ -n "$ALEMBIC_DB" ]] && rm -f "$ALEMBIC_DB"
}
trap cleanup EXIT

section() {
  printf '\n==> %s\n' "$1"
}

if [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
  PYTHON="$BACKEND_DIR/.venv/bin/python"
else
  PYTHON="${PYTHON:-python3}"
fi

if [[ -x "$BACKEND_DIR/.venv/bin/ruff" ]]; then
  RUFF="$BACKEND_DIR/.venv/bin/ruff"
else
  RUFF="${RUFF:-ruff}"
fi

if [[ -x "$BACKEND_DIR/.venv/bin/mypy" ]]; then
  MYPY="$BACKEND_DIR/.venv/bin/mypy"
else
  MYPY="${MYPY:-mypy}"
fi

section "Git whitespace"
git -C "$ROOT_DIR" diff --check

section "Backend lint"
(
  cd "$BACKEND_DIR"
  "$RUFF" check .
  "$RUFF" format --check .
)

section "Backend typecheck"
(
  cd "$BACKEND_DIR"
  "$MYPY" . --ignore-missing-imports
)

section "Backend tests"
PYTEST_DB="$(mktemp -t logopaedie-pytest.XXXXXX.db)"
(
  cd "$BACKEND_DIR"
  DATABASE_URL="sqlite:///$PYTEST_DB" \
    GROQ_API_KEY=test-key-not-real \
    RATE_LIMIT_REDIS_URL=memory:// \
    "$PYTHON" -B -m pytest -q --tb=short -p no:cacheprovider
)

section "Backend migrations"
ALEMBIC_DB="$(mktemp -t logopaedie-alembic.XXXXXX.db)"
(
  cd "$BACKEND_DIR"
  DATABASE_URL="sqlite:///$ALEMBIC_DB" "$PYTHON" -B -m alembic upgrade head
  DATABASE_URL="sqlite:///$ALEMBIC_DB" "$PYTHON" -B -m alembic check
)

section "Frontend lint"
(
  cd "$FRONTEND_DIR"
  npm run lint
)

section "Frontend tests"
(
  cd "$FRONTEND_DIR"
  npm test -- --run
)

section "Frontend typecheck"
(
  cd "$FRONTEND_DIR"
  npx tsc --noEmit
)

section "Frontend build"
(
  cd "$FRONTEND_DIR"
  env -u NEXT_PUBLIC_API_URL \
    -u NEXT_PUBLIC_BACKEND_URL \
    -u BACKEND_URL \
    -u VERCEL \
    -u VERCEL_ENV \
    npm run build
)

section "Presentation script"
"$PYTHON" -B -m py_compile "$ROOT_DIR/scripts/generate_presentation.py"
"$RUFF" check "$ROOT_DIR/scripts/generate_presentation.py"

section "Done"

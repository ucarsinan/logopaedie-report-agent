#!/usr/bin/env bash
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# Cleanup on exit
cleanup() {
  echo -e "\n${YELLOW}Shutting down...${NC}"
  kill 0 2>/dev/null
  exit 0
}
trap cleanup SIGINT SIGTERM

# --- Backend checks ---
echo -e "${BLUE}[Backend]${NC} Checking prerequisites..."

if [ ! -f "$BACKEND_DIR/.env" ]; then
  echo -e "${RED}[Backend]${NC} Missing .env file — copy from .env.example:"
  echo "  cp backend/.env.example backend/.env"
  exit 1
fi

if [ ! -d "$BACKEND_DIR/.venv" ]; then
  echo -e "${YELLOW}[Backend]${NC} Creating virtual environment..."
  python3 -m venv "$BACKEND_DIR/.venv"
fi

echo -e "${BLUE}[Backend]${NC} Installing dependencies..."
"$BACKEND_DIR/.venv/bin/pip" install -q -r "$BACKEND_DIR/requirements.txt"

# --- Frontend checks ---
echo -e "${BLUE}[Frontend]${NC} Checking prerequisites..."

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo -e "${YELLOW}[Frontend]${NC} Installing dependencies..."
  (cd "$FRONTEND_DIR" && npm install)
fi

# --- Start services ---
echo -e "\n${GREEN}Starting services...${NC}\n"

(
  echo -e "${BLUE}[Backend]${NC} Starting uvicorn on :8001"
  cd "$BACKEND_DIR"
  .venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8001 2>&1 | sed "s/^/[Backend] /"
) &

(
  echo -e "${BLUE}[Frontend]${NC} Starting Next.js on :3000"
  cd "$FRONTEND_DIR"
  npm run dev 2>&1 | sed "s/^/[Frontend] /"
) &

echo -e "${GREEN}Backend:${NC}  http://localhost:8001"
echo -e "${GREEN}Frontend:${NC} http://localhost:3000"
echo -e "${YELLOW}Press Ctrl+C to stop both services${NC}\n"

wait

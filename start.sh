#!/usr/bin/env bash
# start.sh — launches the Albion auto-seller stack
# Usage: ./start.sh [--dev]
#   --dev   serve frontend via `ng serve` (port 4200) instead of pre-building

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

DEV_MODE=false
for arg in "$@"; do
  [[ "$arg" == "--dev" ]] && DEV_MODE=true
done

# ── colours ────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[start]${NC} $*"; }
warn()    { echo -e "${YELLOW}[warn]${NC}  $*"; }
error()   { echo -e "${RED}[error]${NC} $*"; }

# ── cleanup on exit ─────────────────────────────────────────────────────────
PIDS=()
cleanup() {
  echo ""
  info "Shutting down all services..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null && wait "$pid" 2>/dev/null || true
  done
  info "All services stopped."
}
trap cleanup EXIT INT TERM

# ── 1. check MongoDB ─────────────────────────────────────────────────────────
info "Checking MongoDB..."
if ! command -v mongosh &>/dev/null && ! command -v mongo &>/dev/null; then
  warn "mongosh/mongo not found in PATH — assuming MongoDB is already running."
else
  MONGO_CMD=$(command -v mongosh 2>/dev/null || command -v mongo)
  if ! "$MONGO_CMD" --eval "db.runCommand({ping:1})" --quiet &>/dev/null; then
    error "MongoDB is not reachable on localhost:27017. Please start it first."
    exit 1
  fi
  info "MongoDB: connected."
fi

# ── 2. frontend ──────────────────────────────────────────────────────────────
if $DEV_MODE; then
  info "Starting Angular dev server (port 4200)..."
  cd "$SCRIPT_DIR/frontend"
  npm install --silent
  npm start > "$LOG_DIR/frontend.log" 2>&1 &
  PIDS+=($!)
  info "Frontend log: logs/frontend.log"
  cd "$SCRIPT_DIR"
else
  info "Building frontend..."
  cd "$SCRIPT_DIR/frontend"
  npm install --silent
  npm run build
  info "Frontend build complete."
  cd "$SCRIPT_DIR"
fi

# ── 3. backend ───────────────────────────────────────────────────────────────
info "Starting Go backend (port ${PORT:-8080})..."
cd "$SCRIPT_DIR/backend"
go run ./cmd/server > "$LOG_DIR/backend.log" 2>&1 &
PIDS+=($!)
info "Backend log: logs/backend.log"
cd "$SCRIPT_DIR"

# ── 4. ready ─────────────────────────────────────────────────────────────────
echo ""
if $DEV_MODE; then
  info "Stack is up:"
  info "  Frontend  →  http://localhost:4200  (dev)"
  info "  Backend   →  http://localhost:${PORT:-8080}"
else
  info "Stack is up:"
  info "  App       →  http://localhost:${PORT:-8080}"
fi
info "Press Ctrl+C to stop all services."
echo ""

# ── 5. tail logs ─────────────────────────────────────────────────────────────
tail -f "$LOG_DIR/backend.log" &
PIDS+=($!)
if $DEV_MODE; then
  tail -f "$LOG_DIR/frontend.log" &
  PIDS+=($!)
fi

# wait for Ctrl+C
wait

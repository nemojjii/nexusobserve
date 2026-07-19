#!/usr/bin/env bash
# run_demo.sh — one command to start Nexus end-to-end.
#
#   ./run_demo.sh
#
# Starts the Collector, loads demo data, opens Dashboard Lite.
# Press Ctrl+C to stop everything.
#
# Prerequisites (first time only):
#   pip install -e nexusobserve -e collector
#   cd dashboard-lite && npm install && cd ..

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_PORT=8000
DASHBOARD_PORT=5173
DB_PATH="$REPO_ROOT/nexus_dev.db"

SERVER_PID=""
DASHBOARD_PID=""

# ── colour output ────────────────────────────────────────────────────────────
_green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
_yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
_red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
_bold()   { printf '\033[1m%s\033[0m\n'   "$*"; }
_step()   { printf '\033[1m[%s/3]\033[0m %s\n' "$1" "$2"; }

# ── cleanup on Ctrl+C / TERM ─────────────────────────────────────────────────
cleanup() {
  printf '\n'
  _yellow "Shutting down Nexus…"
  [ -n "$SERVER_PID" ]    && kill "$SERVER_PID"    2>/dev/null || true
  if [ -n "$DASHBOARD_PID" ]; then
    pkill -P "$DASHBOARD_PID" 2>/dev/null || true
    kill "$DASHBOARD_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  _yellow "Goodbye."
  exit 0
}
trap cleanup INT TERM

# ── detect Python / uvicorn ──────────────────────────────────────────────────
if   [ -x "$REPO_ROOT/.venv/bin/uvicorn" ]; then
  PYTHON="$REPO_ROOT/.venv/bin/python"
  UVICORN="$REPO_ROOT/.venv/bin/uvicorn"
elif [ -x "$REPO_ROOT/venv/bin/uvicorn" ]; then
  PYTHON="$REPO_ROOT/venv/bin/python"
  UVICORN="$REPO_ROOT/venv/bin/uvicorn"
else
  PYTHON="${PYTHON:-python3}"
  UVICORN="${UVICORN:-uvicorn}"
fi

if ! command -v "$UVICORN" > /dev/null 2>&1; then
  _red "ERROR: uvicorn not found."
  _red "       Run:  pip install -e collector"
  exit 1
fi
if ! command -v npm > /dev/null 2>&1; then
  _red "ERROR: npm not found. Install Node.js to run the dashboard."
  exit 1
fi

export PYTHONPATH="$REPO_ROOT/collector:$REPO_ROOT/nexusobserve:$REPO_ROOT"
export NEXUS_DB_PATH="$DB_PATH"
export NEXUS_SERVER="http://127.0.0.1:$SERVER_PORT"

printf '\n'
_bold "  Nexus Decision Observatory"
printf '\n'

# ── 1. Collector ──────────────────────────────────────────────────────────────
_step 1 "Starting Collector (port $SERVER_PORT)…"

rm -f "$DB_PATH"

"$UVICORN" nexus_collector.main:app \
  --host 127.0.0.1 \
  --port "$SERVER_PORT" \
  --log-level warning \
  2>&1 &
SERVER_PID=$!

printf '      waiting for /health'
attempts=0
while ! curl -sf "http://127.0.0.1:$SERVER_PORT/health" > /dev/null 2>&1; do
  sleep 0.25
  printf '.'
  attempts=$((attempts + 1))
  if [ "$attempts" -ge 60 ]; then
    printf '\n'
    _red "ERROR: Collector did not become ready within 15 s."
    _red "       Run:  pip install -e collector"
    cleanup
  fi
done
printf '\n'
_green "      Collector ready ✓  →  http://127.0.0.1:$SERVER_PORT"

# ── 2. Demo data ──────────────────────────────────────────────────────────────
_step 2 "Loading demo data (ORD-1042 · \$500 · gold · 4 candidates)…"

"$PYTHON" "$REPO_ROOT/examples/refund_agent/refund_agent.py"

# ── 3. Dashboard Lite ─────────────────────────────────────────────────────────
_step 3 "Starting Dashboard Lite (port $DASHBOARD_PORT)…"

if [ ! -d "$REPO_ROOT/dashboard-lite/node_modules" ]; then
  _yellow "      node_modules not found — running npm install first…"
  ( cd "$REPO_ROOT/dashboard-lite" && npm install --silent )
fi

( cd "$REPO_ROOT/dashboard-lite" && npm run dev -- --port "$DASHBOARD_PORT" ) &
DASHBOARD_PID=$!

sleep 1.5

printf '\n'
_green "┌────────────────────────────────────────────────────┐"
_green "│  Nexus is running                                  │"
_green "│  Dashboard  →  http://localhost:$DASHBOARD_PORT              │"
_green "│  Collector  →  http://localhost:$SERVER_PORT              │"
_green "│                                                    │"
_green "│  Click a grey alternative node to open the        │"
_green "│  replay diff panel.                               │"
_green "│                                                    │"
_green "│  Press Ctrl+C to stop all processes.              │"
_green "└────────────────────────────────────────────────────┘"
printf '\n'

wait

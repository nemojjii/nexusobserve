#!/usr/bin/env bash
# run_demo.sh — one command to start Nexus end-to-end.
#
#   ./run_demo.sh
#
# Starts the server, loads demo data, opens the dashboard.
# Press Ctrl+C to stop everything.
#
# Prerequisites (first time only):
#   pip install -e packages/sdk -e packages/server
#   cd packages/dashboard && npm install && cd ../..

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_PORT=8000
DASHBOARD_PORT=5173
DB_PATH="$REPO_ROOT/nexus_dev.db"

SERVER_PID=""
DASHBOARD_PID=""

# ── colour output ──────────────────────────────────────────────────────────
_green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
_yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
_red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
_bold()   { printf '\033[1m%s\033[0m\n'   "$*"; }
_step()   { printf '\033[1m[%s/3]\033[0m %s\n' "$1" "$2"; }

# ── cleanup on Ctrl+C / TERM ───────────────────────────────────��───────────
cleanup() {
  printf '\n'
  _yellow "Shutting down Nexus…"
  # Kill server
  [ -n "$SERVER_PID" ]    && kill "$SERVER_PID"    2>/dev/null || true
  # Kill npm process and its children (Vite spawned by npm run dev)
  if [ -n "$DASHBOARD_PID" ]; then
    pkill -P "$DASHBOARD_PID" 2>/dev/null || true
    kill "$DASHBOARD_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  _yellow "Goodbye."
  exit 0
}
trap cleanup INT TERM

# ── detect Python / uvicorn ────────────────────────────────────���───────────
# Prefer a repo-local venv; fall back to anything on PATH.
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

# Sanity checks
if ! command -v "$UVICORN" > /dev/null 2>&1; then
  _red "ERROR: uvicorn not found."
  _red "       Run:  pip install -e packages/server"
  exit 1
fi
if ! command -v npm > /dev/null 2>&1; then
  _red "ERROR: npm not found. Install Node.js to run the dashboard."
  exit 1
fi

# Export for server and demo agent
export PYTHONPATH="$REPO_ROOT/packages/server:$REPO_ROOT/packages/sdk:$REPO_ROOT"
export NEXUS_DB_PATH="$DB_PATH"
export NEXUS_SERVER="http://127.0.0.1:$SERVER_PORT"

printf '\n'
_bold "  Nexus Decision Observatory"
printf '\n'

# ── 1. Start server ─────────────────────────────────────────────────────────
_step 1 "Starting server (port $SERVER_PORT)…"

rm -f "$DB_PATH"   # fresh DB so the demo is reproducible every run

"$UVICORN" nexus_server.main:app \
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
    _red "ERROR: server did not become ready within 15 s."
    _red "       Check that packages/server is installed:"
    _red "       pip install -e packages/server"
    cleanup
  fi
done
printf '\n'
_green "      server ready ✓  →  http://127.0.0.1:$SERVER_PORT"

# ── 2. Load demo data ────────────────────────────────────────────────────────
_step 2 "Loading demo data (ORD-1042 · \$500 · gold · 4 candidates)…"

"$PYTHON" "$REPO_ROOT/demo/refund_agent.py"

# ── 3. Start dashboard ───────────────────────────────────────────────────────
_step 3 "Starting dashboard (port $DASHBOARD_PORT)…"

if [ ! -d "$REPO_ROOT/packages/dashboard/node_modules" ]; then
  _yellow "      node_modules not found — running npm install first…"
  ( cd "$REPO_ROOT/packages/dashboard" && npm install --silent )
fi

( cd "$REPO_ROOT/packages/dashboard" && npm run dev -- --port "$DASHBOARD_PORT" ) &
DASHBOARD_PID=$!

# Give Vite a moment to print its ready line
sleep 1.5

printf '\n'
_green "┌────────────────────────────────────────────────────┐"
_green "│  Nexus is running                                  │"
_green "│  Dashboard  →  http://localhost:$DASHBOARD_PORT              │"
_green "│  Server     →  http://localhost:$SERVER_PORT              │"
_green "│                                                    │"
_green "│  Click a grey alternative node in the graph       │"
_green "│  to open the replay diff panel.                   │"
_green "│                                                    │"
_green "│  Press Ctrl+C to stop all processes.              │"
_green "└────────────────────────────────────────────────────┘"
printf '\n'

# Wait for both background processes; Ctrl+C fires the trap above.
wait

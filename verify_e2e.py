"""SDK → Server → Replay end-to-end integration test.

Flow
----
1. Start a real uvicorn server on a free local port (file-based SQLite).
2. Run the refund demo agent (order #1042, $500, gold, 4 candidates).
   The SDK makes a real HTTP POST /decisions to the server.
3. GET /runs/{run_id}/decisions — verify the decision was stored.
4. POST /replay {decision_id, "escalate"} — verify the diff.

Assertions
----------
- GET /runs/{run_id}/decisions returns exactly 1 decision
- replay cost_delta == 380  (full_refund $500 − escalate $120)
- replay side_effects_executed == 0
- replayed_tools: order_lookup → REPLAYED, refund_execute → SIMULATED
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time

# ── monorepo path bootstrap ───────────────────────────────────────────────────
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
sys.path.insert(0, os.path.join(_here, "packages", "server"))
sys.path.insert(0, os.path.join(_here, "packages", "sdk"))

# ── temp DB: use a real file so server thread and SDK (in-process requests)
#    share a single, persistent store ──────────────────────────────────────────
_DB_PATH = os.path.join(
    "/private/tmp/claude-501/-Users-iris-Desktop-Hack-Nation/"
    "3d5fe441-4732-4fec-834c-cc19c506eb36/scratchpad",
    "nexus_e2e.db",
)
if os.path.exists(_DB_PATH):
    os.remove(_DB_PATH)
os.environ["NEXUS_DB_PATH"] = _DB_PATH

# ── imports (after env is set so db.DB_PATH picks up the right path) ──────────
import requests as _requests  # noqa: E402 – used for HTTP assertions
import uvicorn  # noqa: E402

from nexus_server.main import app  # noqa: E402
from demo.refund_agent import run_agent  # noqa: E402

# ── helpers ───────────────────────────────────────────────────────────────────

def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _start_server(port: int) -> uvicorn.Server:
    cfg = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(cfg)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    # Poll until the server signals it is ready (max 5 s).
    deadline = time.monotonic() + 5.0
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("uvicorn did not start within 5 s")
        time.sleep(0.05)
    return server


# ── main test logic ───────────────────────────────────────────────────────────

def main() -> None:
    PORT = _free_port()
    BASE = f"http://127.0.0.1:{PORT}"

    # ── 1. Start real server ──────────────────────────────────────────────────
    print(f"[e2e] starting Nexus server on port {PORT}…")
    server = _start_server(PORT)
    health = _requests.get(f"{BASE}/health", timeout=3).json()
    assert health["status"] == "ok", f"health check failed: {health}"
    print(f"[e2e] server up → {BASE}")

    # ── 2. Run demo agent → SDK POSTs to server ───────────────────────────────
    print("[e2e] running refund agent (ORD-1042, $500, gold)…")
    order = {
        "order_id": "ORD-1042",
        "amount": 500.0,
        "customer_tier": "gold",
        "reason_code": "item_not_as_described",
    }
    run_id = "e2e-run-1042"
    record = run_agent(order=order, run_id=run_id, server_url=BASE)

    print(f"[e2e] decision captured:")
    print(f"      decision_id  = {record.decision_id}")
    print(f"      chosen       = {record.chosen['action']}  (cost=${record.chosen['cost']:.2f})")
    print(f"      alternatives = {[a['action'] for a in record.alternatives]}")

    # ── 3. GET /runs/{run_id}/decisions ───────────────────────────────────────
    print("[e2e] fetching stored decisions via GET /runs/{run_id}/decisions…")
    resp = _requests.get(f"{BASE}/runs/{run_id}/decisions", timeout=5)
    assert resp.status_code == 200, f"GET /runs/{run_id}/decisions failed: {resp.text}"
    stored = resp.json()

    assert stored["count"] == 1, (
        f"FAIL: expected 1 stored decision, got {stored['count']}"
    )
    stored_decision = stored["decisions"][0]
    assert stored_decision["decision_id"] == record.decision_id, (
        f"FAIL: stored decision_id mismatch"
    )
    assert len(stored_decision["alternatives"]) == 3, (
        f"FAIL: expected 3 alternatives, got {len(stored_decision['alternatives'])}"
    )
    print(f"PASS: GET /runs/{run_id}/decisions → 1 decision, 3 alternatives")

    # ── 4. POST /replay {decision_id, "escalate"} ─────────────────────────────
    print("[e2e] calling POST /replay with alternative_action='escalate'…")
    replay_resp = _requests.post(
        f"{BASE}/replay",
        data=json.dumps(
            {"decision_id": record.decision_id, "alternative_action": "escalate"}
        ),
        headers={"Content-Type": "application/json"},
        timeout=5,
    )
    assert replay_resp.status_code == 200, f"POST /replay failed: {replay_resp.text}"
    result = replay_resp.json()
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # ── assertions ────────────────────────────────────────────────────────────
    cost_delta = result["cost_delta"]
    assert cost_delta == 380.0, f"FAIL: cost_delta expected 380.0, got {cost_delta!r}"
    print(f"PASS: cost_delta == {cost_delta}")

    side_fx = result["side_effects_executed"]
    assert side_fx == 0, f"FAIL: side_effects_executed expected 0, got {side_fx!r}"
    print(f"PASS: side_effects_executed == {side_fx}")

    tools_by_name = {t["tool"]: t for t in result["replayed_tools"]}

    assert "order_lookup" in tools_by_name, "FAIL: order_lookup missing from replayed_tools"
    assert tools_by_name["order_lookup"]["status"] == "REPLAYED", (
        f"FAIL: order_lookup status expected REPLAYED, got "
        f"{tools_by_name['order_lookup']['status']!r}"
    )
    print("PASS: order_lookup → REPLAYED")

    assert "refund_execute" in tools_by_name, "FAIL: refund_execute missing from replayed_tools"
    assert tools_by_name["refund_execute"]["status"] == "SIMULATED", (
        f"FAIL: refund_execute status expected SIMULATED, got "
        f"{tools_by_name['refund_execute']['status']!r}"
    )
    print("PASS: refund_execute → SIMULATED")

    # ── done ──────────────────────────────────────────────────────────────────
    server.should_exit = True
    print("\nAll e2e assertions passed.")


if __name__ == "__main__":
    main()

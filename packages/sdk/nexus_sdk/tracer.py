"""Tracer — build DecisionRecords and optionally ship them to the Nexus server.

The DecisionRecord schema lives in the repo-root ``contracts`` package (the single
source of truth). This module locates it whether the SDK is imported from an
installed wheel or straight from the monorepo checkout.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------- #
# Import the shared schema. Try a normal import first (if `contracts` is on the
# path); otherwise bootstrap the monorepo root onto sys.path.
# --------------------------------------------------------------------------- #
try:  # pragma: no cover - trivial import plumbing
    from contracts.schema import DecisionRecord
except ModuleNotFoundError:  # pragma: no cover
    _here = os.path.dirname(os.path.abspath(__file__))
    # packages/sdk/nexus_sdk/tracer.py -> repo root is three levels up.
    _repo_root = os.path.abspath(os.path.join(_here, "..", "..", ".."))
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)
    from contracts.schema import DecisionRecord  # type: ignore


def record_decision(
    *,
    run_id: str,
    context: Dict[str, Any],
    chosen: Dict[str, Any],
    alternatives: List[Dict[str, Any]],
    latency_ms: float,
    replay_payload: Optional[Dict[str, Any]] = None,
    server_url: Optional[str] = None,
) -> DecisionRecord:
    """Create a DecisionRecord and, if ``server_url`` is given, POST it.

    Returns the DecisionRecord regardless of whether the network send succeeds;
    shipping is best-effort so instrumentation never breaks the agent.
    """
    record = DecisionRecord(
        run_id=run_id,
        context=context,
        chosen=chosen,
        alternatives=alternatives,
        latency_ms=latency_ms,
        replay_payload=replay_payload or {},
    )

    if server_url:
        _ship(record, server_url)

    return record


def _ship(record: DecisionRecord, server_url: str) -> None:
    """Best-effort POST of a record to ``{server_url}/decisions``.

    On success  → prints "[nexus] decision <id> → server OK"
    On any failure → prints a clear WARNING so the caller knows the dashboard
                     will be empty until the server actually receives the data.
    The agent is never killed regardless of outcome.
    """
    url = server_url.rstrip("/") + "/decisions"
    try:
        try:
            import requests
        except ImportError:
            _warn_unreachable(record.decision_id, "requests package not installed")
            return

        resp = requests.post(
            url,
            data=record.to_json(),
            timeout=5,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        print(
            f"[nexus] decision {record.decision_id} → server OK",
            file=sys.stderr,
        )
    except Exception as exc:  # noqa: BLE001 - fire-and-forget; never crash the agent
        _warn_unreachable(record.decision_id, exc)


def _warn_unreachable(decision_id: str, reason: object) -> None:
    print(
        f"[nexus] WARNING: server unreachable, saved to local file only\n"
        f"        (dashboard will be empty until server receives data)\n"
        f"        decision={decision_id}  reason={reason}",
        file=sys.stderr,
    )


__all__ = ["DecisionRecord", "record_decision"]

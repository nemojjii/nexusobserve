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
    """Best-effort POST of a record to ``{server_url}/decisions``."""
    url = server_url.rstrip("/") + "/decisions"
    try:
        import requests  # imported lazily so the SDK works offline

        requests.post(url, data=record.to_json(), timeout=5,
                      headers={"Content-Type": "application/json"})
    except Exception as exc:  # noqa: BLE001 - never break the agent
        # In a hackathon build we just warn; production would use structured logging.
        print(f"[nexus-sdk] warning: failed to ship decision {record.decision_id}: {exc}",
              file=sys.stderr)


__all__ = ["DecisionRecord", "record_decision"]

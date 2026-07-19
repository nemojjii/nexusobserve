"""Core tracer — build DecisionRecords and ship them to the Collector."""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from .schema import DecisionRecord

# -- Module-level local-mode flag --------------------------------------------
_local_mode: bool = False


def init(*, local: bool = False) -> None:
    """Configure nexusobserve for the current process.

    Call once at process startup, before any ``record_decision`` calls.

    Parameters
    ----------
    local:
        ``True`` → local mode: decisions are saved to a local JSONL file and
        a human-readable opportunity-cost summary is printed to stdout.
        No Collector server is needed.  Equivalent to setting
        ``NEXUSOBSERVE_LOCAL=1`` in the environment.
    """
    global _local_mode
    _local_mode = local


def _is_local() -> bool:
    return _local_mode or os.environ.get("NEXUSOBSERVE_LOCAL", "").strip() == "1"


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
    """Create a DecisionRecord and persist / ship it.

    **Local mode** (``nexusobserve.init(local=True)`` or
    ``NEXUSOBSERVE_LOCAL=1``):
        Saves to ``~/.nexusobserve/decisions.jsonl`` and prints an
        opportunity-cost summary to stdout.  No server required.

    **Server mode** (default):
        If ``server_url`` is provided, POSTs the record to the Collector.
        Falls back gracefully with a WARNING if the server is unreachable.

    Returns the ``DecisionRecord`` regardless of transport outcome so
    instrumentation never crashes the agent.
    """
    record = DecisionRecord(
        run_id=run_id,
        context=context,
        chosen=chosen,
        alternatives=alternatives,
        latency_ms=latency_ms,
        replay_payload=replay_payload or {},
    )

    if _is_local():
        _save_local(record)
    elif server_url:
        _ship(record, server_url)

    return record


# ---------------------------------------------------------------------------
# Local mode helpers
# ---------------------------------------------------------------------------

def _save_local(record: DecisionRecord) -> None:
    from .local_store import save

    path = save(record.to_dict())
    _print_summary(record, stored_path=str(path))


def _print_summary(record: DecisionRecord, stored_path: str) -> None:
    """Print a human-readable opportunity-cost summary to stdout."""
    chosen = record.chosen
    chosen_action = chosen.get("action", "?")
    chosen_cost = float(chosen.get("cost", 0))

    lines = [
        f"[nexus] decision {record.decision_id[:8]}…",
        f"  run_id   : {record.run_id}",
        f"  chosen   : {chosen_action:<20s}  cost=${chosen_cost:.2f}",
        f"  discarded:",
    ]

    for alt in record.alternatives:
        alt_action = alt.get("action", "?")
        alt_cost = float(alt.get("cost", 0))
        opp = alt_cost - chosen_cost
        sign = "+" if opp >= 0 else ""
        lines.append(
            f"    {alt_action:<20s}  cost=${alt_cost:<8.2f}  opp_cost={sign}{opp:.2f}"
        )

    lines.append(f"  latency  : {record.latency_ms:.1f}ms")
    lines.append(f"  stored   → {stored_path}")

    print("\n".join(lines))


# ---------------------------------------------------------------------------
# Server mode helpers
# ---------------------------------------------------------------------------

def _ship(record: DecisionRecord, server_url: str) -> None:
    """Best-effort POST of a record to ``{server_url}/decisions``."""
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
    except Exception as exc:  # noqa: BLE001 — fire-and-forget; never crash the agent
        _warn_unreachable(record.decision_id, exc)


def _warn_unreachable(decision_id: str, reason: object) -> None:
    print(
        f"[nexus] WARNING: server unreachable, saved to local file only\n"
        f"        (dashboard will be empty until server receives data)\n"
        f"        decision={decision_id}  reason={reason}",
        file=sys.stderr,
    )


__all__ = ["DecisionRecord", "init", "record_decision"]

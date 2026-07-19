"""Decision Record schema — bundled with the nexusobserve SDK.

This is the canonical definition for the installed package.  The monorepo's
``contracts/schema.py`` is an identical mirror used by the Collector and tests;
keep the two files in sync when changing the wire format.

Uses only the Python standard library so the package has zero import-time
third-party dependencies.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List
from uuid import uuid4

# Bump this when the wire format changes in a backward-incompatible way.
SCHEMA_VERSION = 1


@dataclass
class DecisionRecord:
    """A single decision point in one agent run.

    Fields
    ------
    decision_id:
        Unique id for this decision (uuid4 string). Auto-generated.
    run_id:
        Groups all decisions belonging to a single agent execution.
    timestamp:
        Unix epoch seconds when the decision was made. Auto-generated.
    context:
        Inputs available at decision time (e.g. order_id, amount, customer_tier).
    chosen:
        The selected option, e.g. ``{"action": "full_refund", "cost": 100, ...}``.
    alternatives:
        The discarded options — the heart of Nexus — each shaped like ``chosen``.
    latency_ms:
        Wall-clock time the agent spent making this decision, in milliseconds.
    replay_payload:
        Tool inputs/outputs and any state needed to later re-run a discarded
        alternative and produce a diff.
    schema_version:
        Wire-format version; lets readers migrate old records.
    """

    run_id: str
    context: Dict[str, Any]
    chosen: Dict[str, Any]
    alternatives: List[Dict[str, Any]]
    latency_ms: float
    decision_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: float = field(default_factory=time.time)
    replay_payload: Dict[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    # -- convenience methods --------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return to_dict(self)

    def to_json(self, **json_kwargs: Any) -> str:
        return to_json(self, **json_kwargs)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionRecord":
        return from_dict(data)

    @classmethod
    def from_json(cls, text: str) -> "DecisionRecord":
        return from_json(text)

    def opportunity_costs(self) -> List[Dict[str, Any]]:
        """Derived: opportunity cost of each discarded alternative.

        Returns a list aligned with ``self.alternatives``, each entry carrying
        ``opportunity_cost = alt.cost - chosen.cost``.  Missing ``cost`` fields
        are treated as ``None`` (uncomparable).
        """
        chosen_cost = self.chosen.get("cost")
        results: List[Dict[str, Any]] = []
        for alt in self.alternatives:
            alt_cost = alt.get("cost")
            if chosen_cost is None or alt_cost is None:
                opp = None
            else:
                opp = alt_cost - chosen_cost
            results.append(
                {
                    "action": alt.get("action"),
                    "cost": alt_cost,
                    "opportunity_cost": opp,
                }
            )
        return results


# ---------------------------------------------------------------------------
# Serialization / deserialization
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = ("run_id", "context", "chosen", "alternatives", "latency_ms")


def to_dict(record: DecisionRecord) -> Dict[str, Any]:
    """Convert a DecisionRecord into a plain JSON-serializable dict."""
    return asdict(record)


def to_json(record: DecisionRecord, **json_kwargs: Any) -> str:
    """Serialize a DecisionRecord to a JSON string."""
    json_kwargs.setdefault("ensure_ascii", False)
    return json.dumps(to_dict(record), **json_kwargs)


def from_dict(data: Dict[str, Any]) -> DecisionRecord:
    """Build a DecisionRecord from a dict, ignoring unknown keys."""
    missing = [f for f in _REQUIRED_FIELDS if f not in data]
    if missing:
        raise KeyError(f"DecisionRecord missing required field(s): {missing}")

    known = {
        "run_id", "context", "chosen", "alternatives", "latency_ms",
        "decision_id", "timestamp", "replay_payload", "schema_version",
    }
    kwargs = {k: v for k, v in data.items() if k in known}
    return DecisionRecord(**kwargs)


def from_json(text: str) -> DecisionRecord:
    """Deserialize a JSON string into a DecisionRecord."""
    return from_dict(json.loads(text))


__all__ = [
    "SCHEMA_VERSION",
    "DecisionRecord",
    "to_dict",
    "to_json",
    "from_dict",
    "from_json",
]

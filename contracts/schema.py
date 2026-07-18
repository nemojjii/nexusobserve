"""Nexus — Decision Record schema (Single Source of Truth).

This module defines the ONE canonical shape of an agent decision that all three
layers (SDK, Server, Dashboard-via-JSON) import and agree on.

Core idea: when an agent picks one option among several candidates, we capture
    - the CHOSEN option,
    - the discarded ALTERNATIVES, and
    - enough replay context to later re-run a discarded alternative and diff it.

Opportunity cost is *derived* (not stored): for each alternative it is
``alternative.cost - chosen.cost`` (or any richer comparison the dashboard wants),
so the schema stores only raw material.

Implementation note: this file uses ONLY the Python standard library
(``dataclasses``, ``json``, ``uuid``, ``time``) so that::

    python -c "from contracts.schema import DecisionRecord; print('ok')"

succeeds with zero third-party dependencies installed. Layers that want richer
validation (server/sdk) can wrap these dataclasses with pydantic on their side.
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

    # -- convenience methods (thin wrappers over the module-level functions) --

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
        """Derived helper: opportunity cost of each discarded alternative.

        Returns a list aligned with ``self.alternatives``, each entry carrying the
        alternative's action and ``opportunity_cost = alt.cost - chosen.cost``.
        Missing ``cost`` fields are treated as ``None`` (uncomparable).
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


# --------------------------------------------------------------------------- #
# Serialization / deserialization
# --------------------------------------------------------------------------- #

# Fields required to reconstruct a record. Auto-generated / defaulted fields are
# optional so partial dicts (e.g. from an SDK caller) still round-trip.
_REQUIRED_FIELDS = ("run_id", "context", "chosen", "alternatives", "latency_ms")


def to_dict(record: DecisionRecord) -> Dict[str, Any]:
    """Convert a DecisionRecord into a plain JSON-serializable dict."""
    return asdict(record)


def to_json(record: DecisionRecord, **json_kwargs: Any) -> str:
    """Serialize a DecisionRecord to a JSON string."""
    json_kwargs.setdefault("ensure_ascii", False)
    return json.dumps(to_dict(record), **json_kwargs)


def from_dict(data: Dict[str, Any]) -> DecisionRecord:
    """Build a DecisionRecord from a dict, ignoring unknown keys.

    Raises ``KeyError`` if a required field is missing.
    """
    missing = [f for f in _REQUIRED_FIELDS if f not in data]
    if missing:
        raise KeyError(f"DecisionRecord missing required field(s): {missing}")

    known = {
        "run_id",
        "context",
        "chosen",
        "alternatives",
        "latency_ms",
        "decision_id",
        "timestamp",
        "replay_payload",
        "schema_version",
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

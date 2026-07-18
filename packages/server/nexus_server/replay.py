"""Nexus replay engine.

Given a stored DecisionRecord and an ``alternative_action`` the caller wants to
explore, this module:

1. **Re-plays query tools** — returns the recorded outputs from ``replay_payload``
   without touching any live system.
2. **Simulates side-effect tools** — marks them ``{"tool": ..., "status": "SIMULATED"}``
   and never executes them. ``side_effects_executed`` in the response is therefore
   always 0.
3. **Calculates a diff** between the original ``chosen`` and the requested
   alternative:
   - ``cost_delta = chosen.cost - alternative.cost``  (positive → alt is cheaper)
   - Any extra tradeoff keys present in ``replay_payload`` (e.g. ``latency_ms``,
     ``processing_delay_ms``) are forwarded in ``tradeoffs``.

Tool classification
-------------------
Each entry in ``replay_payload["tools"]`` can carry an explicit
``"type": "query" | "side_effect"`` field. If absent, the name is matched
against a keyword heuristic. The conservative default is ``"query"`` so nothing
is accidentally silenced.

replay_payload conventions (both forms accepted):

  # Single tool (backward-compat):
  {"tool": "policy_engine.decide", "inputs": {...}, "outputs": {...}, ...}

  # Multi-tool list (preferred):
  {
    "tools": [
      {"name": "order_lookup", "type": "query",       "inputs": {...}, "outputs": {...}},
      {"name": "refund_execute", "type": "side_effect", "inputs": {...}},
    ],
    ...extra tradeoff keys...
  }
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from contracts.schema import DecisionRecord

# Keywords that classify an unnamed tool as a side-effect.
_SIDE_EFFECT_KEYWORDS = frozenset(
    {
        "execute", "send", "email", "refund", "pay", "charge",
        "write", "create", "update", "delete", "post", "push",
        "notify", "trigger", "submit", "commit", "dispatch",
    }
)

# replay_payload keys that are NOT tool descriptors and NOT internal meta —
# anything else is treated as an extra tradeoff to surface in the diff.
_NON_TRADEOFF_KEYS = frozenset({"tool", "tools", "inputs", "outputs", "candidates", "policy"})


def _is_side_effect(tool_entry: Dict[str, Any]) -> bool:
    """Return True if this tool entry represents a side-effecting operation."""
    explicit = tool_entry.get("type")
    if explicit == "side_effect":
        return True
    if explicit == "query":
        return False
    # Heuristic fallback: check name tokens against the keyword list.
    name: str = tool_entry.get("name", tool_entry.get("tool", ""))
    tokens = {t.lower() for t in name.replace(".", "_").split("_")}
    return bool(tokens & _SIDE_EFFECT_KEYWORDS)


def _normalize_tools(replay_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return a flat list of tool entries regardless of which payload form was used."""
    if "tools" in replay_payload:
        return list(replay_payload["tools"])
    if "tool" in replay_payload:
        # Single-tool backward-compat form.
        return [
            {
                "name": replay_payload["tool"],
                "inputs": replay_payload.get("inputs", {}),
                "outputs": replay_payload.get("outputs", {}),
                # No explicit type — let heuristic decide.
            }
        ]
    return []


def _extra_tradeoffs(replay_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract non-tool keys from replay_payload as additional tradeoff signals."""
    return {k: v for k, v in replay_payload.items() if k not in _NON_TRADEOFF_KEYS}


def _find_alternative(
    record: DecisionRecord, alternative_action: str
) -> Optional[Dict[str, Any]]:
    for alt in record.alternatives:
        if alt.get("action") == alternative_action:
            return alt
    return None


def replay_decision(
    record: DecisionRecord,
    alternative_action: str,
) -> Dict[str, Any]:
    """Replay a discarded alternative and return the diff.

    Parameters
    ----------
    record:
        The original DecisionRecord fetched from the store.
    alternative_action:
        The ``action`` string of the discarded alternative to explore.

    Returns
    -------
    dict with keys:
        decision_id, run_id, original_action, replayed_action,
        cost_delta, tradeoffs, replayed_tools, side_effects_executed
    """
    alt = _find_alternative(record, alternative_action)
    if alt is None:
        raise ValueError(
            f"Alternative '{alternative_action}' not found in decision {record.decision_id}. "
            f"Available: {[a.get('action') for a in record.alternatives]}"
        )

    # --- cost diff -------------------------------------------------------
    chosen_cost: Optional[float] = record.chosen.get("cost")
    alt_cost: Optional[float] = alt.get("cost")
    if chosen_cost is not None and alt_cost is not None:
        cost_delta: Optional[float] = float(chosen_cost) - float(alt_cost)
    else:
        cost_delta = None  # uncomparable (cost not recorded)

    # --- tool replay -----------------------------------------------------
    tools = _normalize_tools(record.replay_payload)
    replayed_tools: List[Dict[str, Any]] = []

    for entry in tools:
        name = entry.get("name", entry.get("tool", "unknown"))
        if _is_side_effect(entry):
            # Never execute — return a simulation marker.
            replayed_tools.append(
                {
                    "tool": name,
                    "status": "SIMULATED",
                    "inputs": entry.get("inputs", {}),
                }
            )
        else:
            # Re-play: return the recorded outputs verbatim.
            replayed_tools.append(
                {
                    "tool": name,
                    "status": "REPLAYED",
                    "inputs": entry.get("inputs", {}),
                    "outputs": entry.get("outputs", {}),
                }
            )

    # side_effects_executed is always 0 — this is a contract guarantee.
    side_effects_executed = 0

    # --- extra tradeoffs -------------------------------------------------
    tradeoffs = _extra_tradeoffs(record.replay_payload)
    # Add per-alternative extra fields (anything beyond action/cost).
    for k, v in alt.items():
        if k not in ("action", "cost"):
            tradeoffs[f"alt_{k}"] = v

    return {
        "decision_id": record.decision_id,
        "run_id": record.run_id,
        "original_action": record.chosen.get("action"),
        "replayed_action": alternative_action,
        "cost_delta": cost_delta,
        "tradeoffs": tradeoffs,
        "replayed_tools": replayed_tools,
        "side_effects_executed": side_effects_executed,
    }

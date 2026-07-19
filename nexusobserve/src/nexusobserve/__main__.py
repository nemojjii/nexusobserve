"""python -m nexusobserve [show]

Commands
--------
show    Print all locally stored decisions with opportunity-cost summaries.
        (default when no command is given)
clear   Delete the local decisions file.
"""

from __future__ import annotations

import sys


def _show() -> None:
    from .local_store import load_all, store_path

    records = load_all()
    path = store_path()

    if not records:
        print("No decisions recorded yet.")
        print()
        print("Quick start (no server needed):")
        print()
        print("  import nexusobserve")
        print("  nexusobserve.init(local=True)   # or: NEXUSOBSERVE_LOCAL=1")
        print("  nexusobserve.record_decision(...)")
        print()
        print(f"  Decisions will be stored at: {path}")
        return

    print(f"Stored decisions — {path}")
    print(f"Total: {len(records)}\n")
    print("-" * 60)

    for rec in records:
        decision_id = rec.get("decision_id", "?")
        run_id = rec.get("run_id", "?")
        chosen = rec.get("chosen", {})
        alternatives = rec.get("alternatives", [])
        latency_ms = rec.get("latency_ms", 0)

        chosen_action = chosen.get("action", "?")
        chosen_cost = float(chosen.get("cost", 0))

        print(f"decision : {decision_id}")
        print(f"run_id   : {run_id}")
        print(f"chosen   : {chosen_action:<20s}  cost=${chosen_cost:.2f}")
        print(f"discarded:")
        for alt in alternatives:
            alt_action = alt.get("action", "?")
            alt_cost = float(alt.get("cost", 0))
            opp = alt_cost - chosen_cost
            sign = "+" if opp >= 0 else ""
            print(f"  {alt_action:<20s}  cost=${alt_cost:<8.2f}  opp_cost={sign}{opp:.2f}")
        print(f"latency  : {latency_ms:.1f}ms")
        print("-" * 60)


def _clear() -> None:
    from .local_store import store_path

    path = store_path()
    if path.exists():
        path.unlink()
        print(f"Cleared: {path}")
    else:
        print("Nothing to clear.")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "show":
        _show()
    elif cmd == "clear":
        _clear()
    else:
        print(f"Unknown command: {cmd!r}")
        print("Usage: python -m nexusobserve [show|clear]")
        sys.exit(1)


if __name__ == "__main__":
    main()

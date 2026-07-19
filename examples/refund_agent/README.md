# Example: Refund Agent

A customer-support agent that handles refund requests. Demonstrates how to
instrument an agent with `nexusobserve` to capture decisions.

```bash
# from repo root
python examples/refund_agent/refund_agent.py

# ship to a running Collector
NEXUS_SERVER=http://localhost:8000 python examples/refund_agent/refund_agent.py
```

The agent considers four candidates (full refund / partial refund / escalate /
deny+coupon), picks `full_refund` for gold-tier customers, and records the
decision with all discarded alternatives and a `replay_payload` that marks
`refund_execute` as a side-effect tool (→ `SIMULATED` on replay).

# Nexus — AI Agent Decision Observability

[![CI](https://github.com/nemojjii/nexus/actions/workflows/ci.yml/badge.svg)](https://github.com/nemojjii/nexus/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> When an AI agent picks one option among several candidates, most tools only log what it *did*.
> **Nexus captures what it *didn't* do too** — chosen option + discarded alternatives + opportunity cost — and lets you **replay** any discarded alternative to diff the outcome.

```
chosen + discarded alternatives + opportunity cost  →  replay  →  diff
```

## 30-second example — no server needed

```bash
pip install nexusobserve
```

```python
import nexusobserve

nexusobserve.init(local=True)          # or set env var NEXUSOBSERVE_LOCAL=1

nexusobserve.record_decision(
    run_id="order-run-001",
    context={"order_id": "ORD-1042", "amount": 500, "tier": "gold"},
    chosen={"action": "full_refund", "cost": 500.0},
    alternatives=[
        {"action": "partial_refund", "cost": 200.0},
        {"action": "escalate",       "cost": 120.0},
        {"action": "deny+coupon",    "cost":  30.0},
    ],
    latency_ms=12.3,
)
```

Running this prints straight to the terminal — no server, no signup required:

```
[nexus] decision a1b2c3d4…
  run_id   : order-run-001
  chosen   : full_refund           cost=$500.00
  discarded:
    partial_refund        cost=$200.00    opp_cost=-300.00
    escalate              cost=$120.00    opp_cost=-380.00
    deny+coupon           cost=$30.00     opp_cost=-470.00
  latency  : 12.3ms
  stored   → ~/.nexusobserve/decisions.jsonl
```

To view recorded decisions:

```bash
python -m nexusobserve show
```

To hook up a Collector server, just add the `server_url` parameter:

```python
nexusobserve.record_decision(..., server_url="http://localhost:8000")
```

## One-shot run

```bash
./run_demo.sh
```

Starts the server → loads demo data → opens the dashboard, all in one go.
A single `Ctrl+C` cleans up all processes.

| Access | URL |
|---|---|
| Dashboard | http://localhost:5173 |
| Collector API | http://localhost:8000 |

Click a grey alternative node on the dashboard to open the replay diff panel.

---

## Repo structure

```
nexusobserve/          SDK — pip install nexusobserve
collector/              Collector — FastAPI + SQLite (pip install nexus-collector)
dashboard-lite/         Single-run bubble graph + diff (npm run dev)
examples/
  refund_agent/         Demo agent
contracts/schema.py     DecisionRecord — single source of truth (SSOT) across all three layers
docs/
  ARCHITECTURE.md
  related-work.md
run_demo.sh             ← start here
LICENSE                 MIT
```

**Private (future Nexus hosting):** aggregation · auth · multi-tenancy · retention · team features

---

## Architecture

```
        ┌──────────────────────────────────────────────────────────────┐
        │                    contracts/schema.py                        │
        │     DecisionRecord — Single Source of Truth (SSOT)            │
        └──────────────────────────────────────────────────────────────┘
                  ▲                    ▲                     ▲
                  │ import             │ import              │ JSON / HTTP
   ┌──────────────┴──────────┐ ┌───────┴────────────┐ ┌─────┴──────────────────┐
   │  nexusobserve  (SDK)    │ │  collector         │ │  dashboard-lite        │
   │  record_decision()      │▶│  FastAPI + SQLite  │▶│  force-graph + replay  │
   └─────────────────────────┘ └────────────────────┘ └────────────────────────┘
```

1. **SDK** (`nexusobserve`) — instrument an agent with a single line: `record_decision(...)`.
2. **Collector** (`nexus-collector`) — stores decision records in SQLite. Built-in replay engine.
3. **Dashboard Lite** — per-run decision bubble graph; click an alternative → shows cost_delta + a SIMULATED badge.

---

## DecisionRecord schema

Defined in `contracts/schema.py` using only the standard library. Importable with no dependencies.

| Field | Type | Description |
|---|---|---|
| `decision_id` | str | uuid4 (auto-generated) |
| `run_id` | str | ID grouping a single agent run |
| `timestamp` | float | Unix epoch (auto) |
| `context` | dict | Input values at decision time |
| `chosen` | dict | The selected alternative `{action, cost, …}` |
| `alternatives` | list | **The discarded alternatives** `[{action, cost, …}, …]` |
| `latency_ms` | float | Time taken to reach the decision |
| `replay_payload` | dict | Recorded tool inputs/outputs for replay |
| `schema_version` | int | Wire format version |

Opportunity cost is a derived calculation: `alternative.cost − chosen.cost` → `DecisionRecord.opportunity_costs()`

---

## First-time setup (once)

```bash
pip install -e nexusobserve -e collector
cd dashboard-lite && npm install && cd ..
```

## Manual run

```bash
# Terminal A — Collector
PYTHONPATH="collector:." NEXUS_DB_PATH=nexus.db \
  uvicorn nexus_collector.main:app --reload

# Terminal B — Demo agent
NEXUS_SERVER=http://localhost:8000 \
  python examples/refund_agent/refund_agent.py

# Terminal C — Dashboard
cd dashboard-lite && npm run dev
```

## Schema validation

```bash
python -c "from contracts.schema import DecisionRecord; print('ok')"
```

## Contributing

Issues and pull requests are welcome. Please open an issue to discuss significant changes before submitting a PR.

## License

[MIT](LICENSE)

---

*See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/related-work.md`](docs/related-work.md) for design rationale.*



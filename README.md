# Nexus — AI Agent Decision Observability

When an AI agent picks one option among several candidates, most tools only log
what it *did*. **Nexus captures what it *didn't* do too** — the chosen option,
the discarded alternatives, and each alternative's opportunity cost — and keeps
enough state to **replay** a discarded alternative later and diff the outcome.

> chosen + discarded alternatives + opportunity cost → replay → diff

## Monorepo layout

```
contracts/schema.py     ← DecisionRecord: the single source of truth (SSOT)
packages/
  sdk/                  Python package — instrument an agent (pip install -e)
  server/               FastAPI + SQLite — ingest & serve decision records
  dashboard/            React + react-force-graph — visualize + replay (later)
demo/
  refund_agent.py       example refund agent instrumented with the SDK
docs/
  ARCHITECTURE.md       deeper architecture notes
```

## Three-layer architecture

```
        ┌──────────────────────────────────────────────────────────────┐
        │                    contracts/schema.py                        │
        │     DecisionRecord — the single source of truth (SSOT)        │
        └──────────────────────────────────────────────────────────────┘
                  ▲                    ▲                     ▲
                  │ import             │ import              │ JSON / HTTP
   ┌──────────────┴───────┐  ┌─────────┴──────────┐  ┌───────┴───────────────┐
   │  SDK                 │  │  Server            │  │  Dashboard            │
   │  (agent instrument)  │─▶│  FastAPI + SQLite  │─▶│  React + force-graph  │
   │  record_decision()   │  │  /decisions,/runs  │  │  visualize + replay   │
   └──────────────────────┘  └────────────────────┘  └───────────────────────┘
```

1. **SDK** — `record_decision(...)` builds a `DecisionRecord` inside the agent
   and optionally ships it to the server.
2. **Server** — FastAPI stores records in SQLite as JSON blobs indexed by `run_id`.
3. **Dashboard** — renders each run as a decision graph (chosen vs. discarded,
   weighted by opportunity cost); replay/diff lives here. *(later)*

## The DecisionRecord schema

Defined once in [`contracts/schema.py`](contracts/schema.py) using only the
Python standard library, so it imports with **zero dependencies installed**.

| Field            | Type  | Meaning                                                      |
|------------------|-------|--------------------------------------------------------------|
| `decision_id`    | str   | uuid4 for this decision (auto)                               |
| `run_id`         | str   | groups all decisions in one agent execution                 |
| `timestamp`      | float | unix epoch seconds (auto)                                   |
| `context`        | dict  | inputs at decision time (order_id, amount, customer_tier…)  |
| `chosen`         | dict  | the selected option `{action, cost, …}`                     |
| `alternatives`   | list  | discarded options `[{action, cost, …}, …]` — **the core**   |
| `latency_ms`     | float | time the agent spent deciding                               |
| `replay_payload` | dict  | tool I/O & state to re-run a discarded alternative          |
| `schema_version` | int   | wire-format version for migration                           |

Serialization helpers: `to_dict` / `to_json` / `from_dict` / `from_json` (plus
matching methods on the dataclass). **Opportunity cost is derived**
(`alternative.cost - chosen.cost`) via `DecisionRecord.opportunity_costs()`.

## Quick start

```bash
# 1. Verify the shared schema imports with no dependencies
python -c "from contracts.schema import DecisionRecord; print('ok')"

# 2. Install the SDK (editable)
pip install -e packages/sdk

# 3. Run the demo agent (prints chosen + opportunity costs)
python demo/refund_agent.py

# 4. (optional) Run the server, then ship demo records to it
pip install -e packages/server
uvicorn nexus_server.main:app --reload            # terminal A
NEXUS_SERVER=http://localhost:8000 python demo/refund_agent.py   # terminal B
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for more.

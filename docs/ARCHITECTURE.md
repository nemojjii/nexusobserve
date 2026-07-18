# Nexus Architecture

Nexus is a **decision observability** tool for AI agents. Whenever an agent picks
one option among several candidates, Nexus captures **the chosen option, the
discarded alternatives, and each alternative's opportunity cost** — and keeps
enough state to *replay* a discarded alternative later and diff the outcome.

## Three-layer architecture

```
        ┌──────────────────────────────────────────────────────────────┐
        │                    contracts/schema.py                        │
        │     DecisionRecord — the single source of truth (SSOT)        │
        │   imported / mirrored by every layer via JSON serialization   │
        └──────────────────────────────────────────────────────────────┘
                  ▲                    ▲                     ▲
                  │ import             │ import              │ JSON over HTTP
                  │                    │                     │
   ┌──────────────┴───────┐  ┌─────────┴──────────┐  ┌───────┴───────────────┐
   │  packages/sdk        │  │  packages/server   │  │  packages/dashboard   │
   │  (agent instrument)  │─▶│  FastAPI + SQLite  │─▶│  React + force-graph  │
   │  record_decision()   │  │  /decisions, /runs │  │  visualize + replay   │
   └──────────────────────┘  └────────────────────┘  └───────────────────────┘
            captures                 stores                    explores

   demo/refund_agent.py — an example agent instrumented with the SDK.
```

1. **SDK (`packages/sdk`)** — imported into the agent. `record_decision(...)`
   builds a `DecisionRecord` and (optionally) POSTs it to the server.
2. **Server (`packages/server`)** — FastAPI ingests records and stores them in
   SQLite as JSON blobs, indexed by `run_id`.
3. **Dashboard (`packages/dashboard`)** — React + `react-force-graph` renders a
   run as a graph of decisions; each decision fans out into chosen + discarded
   alternatives, with opportunity cost on the edges. Replay lives here (later).

## The DecisionRecord (owned by `contracts/schema.py`)

| Field            | Type    | Meaning                                                        |
|------------------|---------|----------------------------------------------------------------|
| `decision_id`    | str     | uuid4 for this decision (auto)                                 |
| `run_id`         | str     | groups all decisions in one agent execution                    |
| `timestamp`      | float   | unix epoch seconds (auto)                                      |
| `context`        | dict    | inputs at decision time (order_id, amount, customer_tier, …)   |
| `chosen`         | dict    | the selected option `{action, cost, …}`                        |
| `alternatives`   | list    | discarded options `[{action, cost, …}, …]` — **the core**      |
| `latency_ms`     | float   | time the agent spent deciding                                  |
| `replay_payload` | dict    | tool inputs/outputs & state needed to re-run an alternative    |
| `schema_version` | int     | wire-format version for migration                              |

**Opportunity cost is derived, not stored:** for each alternative it is
`alternative.cost - chosen.cost` (see `DecisionRecord.opportunity_costs()`), so
the schema keeps only raw material and the dashboard is free to define richer
comparisons.

## Why a single shared schema?

All three layers depend on one file. The SDK and server import it directly; the
dashboard consumes the same shape over JSON. Change the shape in exactly one
place and every layer moves together.

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

## Quick start — 한 방

```bash
./run_demo.sh
```

서버 기동 → 데모 데이터 적재 → 대시보드 오픈까지 한 번에 실행됩니다.
`Ctrl+C` 한 번으로 서버·대시보드 프로세스를 모두 정리합니다.

| 접속 | 주소 |
|---|---|
| 대시보드 | http://localhost:5173 |
| API 서버 | http://localhost:8000 |

대시보드에서 회색 대안 노드(escalate, partial_refund 등)를 클릭하면 오른쪽에
replay diff 패널이 열립니다.

### 최초 설치 (한 번만)

```bash
# Python 의존성
pip install -e packages/sdk -e packages/server

# 대시보드 Node 의존성
cd packages/dashboard && npm install && cd ../..
```

### 수동 실행 (터미널 분리 운용)

```bash
# 터미널 A — 서버
PYTHONPATH="packages/server:." NEXUS_DB_PATH=nexus.db \
  uvicorn nexus_server.main:app --reload

# 터미널 B — 데모 데이터 적재
NEXUS_SERVER=http://localhost:8000 python demo/refund_agent.py

# 터미널 C — 대시보드
cd packages/dashboard && npm run dev
```

### 스키마 검증

```bash
python -c "from contracts.schema import DecisionRecord; print('ok')"
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for more.

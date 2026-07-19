# Nexus — AI Agent Decision Observability

[![CI](https://github.com/nemojjii/nexus/actions/workflows/ci.yml/badge.svg)](https://github.com/nemojjii/nexus/actions/workflows/ci.yml)

> When an AI agent picks one option among several candidates, most tools only log what it *did*.  
> **Nexus captures what it *didn't* do too** — chosen option + discarded alternatives + opportunity cost — and lets you **replay** any discarded alternative to diff the outcome.

```
chosen + discarded alternatives + opportunity cost  →  replay  →  diff
```

## 30초 예제 — 서버 없이 바로

```bash
pip install nexusobserve
```

```python
import nexusobserve

nexusobserve.init(local=True)          # 또는 환경변수 NEXUSOBSERVE_LOCAL=1

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

실행하면 터미널에 즉시 출력됩니다 — 서버·가입 불필요:

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

기록된 결정 목록 조회:

```bash
python -m nexusobserve show
```

Collector 서버와 연동하려면 `server_url` 파라미터를 추가하기만 하면 됩니다:

```python
nexusobserve.record_decision(..., server_url="http://localhost:8000")
```

## 한 방 실행

```bash
./run_demo.sh
```

서버 기동 → 데모 데이터 적재 → 대시보드 오픈까지 한 번에.  
`Ctrl+C` 한 번으로 모든 프로세스 정리.

| 접속 | 주소 |
|---|---|
| 대시보드 | http://localhost:5173 |
| Collector API | http://localhost:8000 |

대시보드에서 회색 대안 노드를 클릭하면 replay diff 패널이 열립니다.

---

## 리포 구조

```
nexusobserve/          SDK — pip install nexusobserve
collector/             Collector — FastAPI + SQLite (pip install nexus-collector)
dashboard-lite/        단일 런 버블그래프 + diff (npm run dev)
examples/
  refund_agent/        데모 에이전트
contracts/schema.py    DecisionRecord — 세 계층의 단일 진실 원천(SSOT)
docs/
  ARCHITECTURE.md
  related-work.md
run_demo.sh            ← 여기서 시작
LICENSE                MIT
```

**비공개 (추후 Nexus 호스팅):** 집계 · 인증 · 멀티테넌시 · 보관 · 팀 기능

---

## 아키텍처

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

1. **SDK** (`nexusobserve`) — `record_decision(...)` 한 줄로 에이전트를 계측.
2. **Collector** (`nexus-collector`) — 결정 레코드를 SQLite에 저장. replay 엔진 내장.
3. **Dashboard Lite** — 런별 결정 버블그래프; 대안 클릭 → cost_delta + SIMULATED 배지.

---

## DecisionRecord 스키마

`contracts/schema.py` 에 표준 라이브러리만으로 정의. 의존성 없이 import 가능.

| 필드 | 타입 | 설명 |
|---|---|---|
| `decision_id` | str | uuid4 (자동 생성) |
| `run_id` | str | 한 번의 에이전트 실행을 묶는 ID |
| `timestamp` | float | 유닉스 에폭(자동) |
| `context` | dict | 결정 당시 입력값 |
| `chosen` | dict | 선택된 대안 `{action, cost, …}` |
| `alternatives` | list | **버려진 대안들** `[{action, cost, …}, …]` |
| `latency_ms` | float | 결정에 걸린 시간 |
| `replay_payload` | dict | 재실행용 툴 입출력 기록 |
| `schema_version` | int | 와이어 포맷 버전 |

기회비용은 파생 계산: `alternative.cost − chosen.cost` → `DecisionRecord.opportunity_costs()`

---

## 최초 설치 (한 번만)

```bash
pip install -e nexusobserve -e collector
cd dashboard-lite && npm install && cd ..
```

## 수동 실행

```bash
# 터미널 A — Collector
PYTHONPATH="collector:." NEXUS_DB_PATH=nexus.db \
  uvicorn nexus_collector.main:app --reload

# 터미널 B — 데모 에이전트
NEXUS_SERVER=http://localhost:8000 \
  python examples/refund_agent/refund_agent.py

# 터미널 C — 대시보드
cd dashboard-lite && npm run dev
```

## 스키마 검증

```bash
python -c "from contracts.schema import DecisionRecord; print('ok')"
```

## License

[MIT](LICENSE)

---

*See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/related-work.md`](docs/related-work.md) for design rationale.*

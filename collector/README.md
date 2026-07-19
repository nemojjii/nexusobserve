# nexus-collector

Lightweight FastAPI + SQLite collector for Nexus decision records.

```bash
pip install nexus-collector
uvicorn nexus_collector.main:app --reload
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/decisions` | Ingest one `DecisionRecord` |
| GET | `/runs` | List all run IDs |
| GET | `/runs/{run_id}/decisions` | All decisions for a run |
| POST | `/replay` | Replay a discarded alternative |
| GET | `/health` | Health check |

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `NEXUS_DB_PATH` | `nexus.db` | SQLite database path (`:memory:` for tests) |

## Replay

```bash
curl -X POST http://localhost:8000/replay \
  -H 'Content-Type: application/json' \
  -d '{"decision_id": "<uuid>", "alternative_action": "escalate"}'
```

Response:
```json
{
  "cost_delta": 380.0,
  "side_effects_executed": 0,
  "replayed_tools": [
    {"tool": "order_lookup",  "status": "REPLAYED",  "outputs": {...}},
    {"tool": "refund_execute","status": "SIMULATED"}
  ]
}
```

`cost_delta` is computed purely from captured values — no LLM calls.  
`side_effects_executed` is always `0` by contract.

> **Hosted tier** (aggregate analytics, auth, multi-tenancy, retention) → Nexus Cloud

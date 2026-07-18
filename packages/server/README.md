# nexus-server

FastAPI + SQLite store for Nexus decision records.

```bash
pip install -e packages/server
uvicorn nexus_server.main:app --reload   # run from repo root
```

Endpoints (stub):

| Method | Path                     | Purpose                                  |
|--------|--------------------------|------------------------------------------|
| POST   | `/decisions`             | Store one `DecisionRecord` (JSON body)   |
| GET    | `/decisions/{run_id}`    | List all decisions for one agent run     |
| GET    | `/runs`                  | List known run ids                       |

Records are stored as JSON blobs keyed by `decision_id`, indexed by `run_id`, so
the shared `contracts/schema.py` stays the single source of truth for shape.

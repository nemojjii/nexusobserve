"""FastAPI app for Nexus — ingest and serve agent decision records.

Stub implementation for the hackathon: enough to receive records from the SDK
and serve them to the dashboard. The record shape is owned by the repo-root
``contracts`` package (single source of truth).
"""

from __future__ import annotations

import json
import os
import sys

# Bootstrap the monorepo root so `contracts` is importable when run from anywhere.
_here = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.abspath(os.path.join(_here, "..", "..", ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from contracts.schema import DecisionRecord, from_dict, from_json  # noqa: E402

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from . import db  # noqa: E402
from .replay import replay_decision  # noqa: E402

app = FastAPI(title="Nexus Server", version="0.1.0")

# The dashboard (React) runs on a different origin during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/decisions")
async def create_decision(request: Request) -> dict:
    """Store one DecisionRecord (validated against the shared schema)."""
    raw = await request.body()
    try:
        record: DecisionRecord = from_dict(json.loads(raw))
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid DecisionRecord: {exc}")

    db.insert_decision(
        decision_id=record.decision_id,
        run_id=record.run_id,
        timestamp=record.timestamp,
        payload_json=record.to_json(),
    )
    return {"decision_id": record.decision_id, "run_id": record.run_id}


@app.get("/decisions/{run_id}")
def get_run(run_id: str) -> dict:
    """Return all decisions for a single agent run."""
    payloads = db.get_decisions_for_run(run_id)
    decisions = [json.loads(p) for p in payloads]
    return {"run_id": run_id, "count": len(decisions), "decisions": decisions}


@app.get("/runs")
def list_runs() -> dict:
    return {"runs": db.list_run_ids()}


@app.post("/replay")
async def replay(request: Request) -> dict:
    """Replay a discarded alternative and return the diff.

    Request body JSON:
        {"decision_id": "<uuid>", "alternative_action": "<action string>"}

    Response includes:
        cost_delta          — chosen.cost - alt.cost  (always from captured values, no LLM)
        tradeoffs           — any extra fields from replay_payload
        replayed_tools      — query tools: recorded outputs; side-effect tools: SIMULATED
        side_effects_executed — always 0 (contract guarantee)
    """
    try:
        body = json.loads(await request.body())
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid JSON: {exc}")

    decision_id = body.get("decision_id")
    alternative_action = body.get("alternative_action")
    if not decision_id or not alternative_action:
        raise HTTPException(
            status_code=422,
            detail="request must include 'decision_id' and 'alternative_action'",
        )

    payload_json = db.get_decision_by_id(decision_id)
    if payload_json is None:
        raise HTTPException(status_code=404, detail=f"decision '{decision_id}' not found")

    try:
        record: DecisionRecord = from_json(payload_json)
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"corrupt stored record: {exc}")

    try:
        result = replay_decision(record, alternative_action)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return result

# nexus-dashboard

React + `react-force-graph` visualization of agent decisions.

> **Status: 나중에 (later).** This package is a placeholder. The plan is to render
> each `DecisionRecord` as a node whose children are the chosen option and the
> discarded alternatives, with edge weight = opportunity cost, and a "replay"
> action that re-runs a discarded alternative to produce a diff.

Planned setup:

```bash
cd packages/dashboard
npm install
npm run dev
```

Data source: the Nexus server's `GET /decisions/{run_id}` endpoint. The record
shape it consumes is defined once in the repo-root `contracts/schema.py`.

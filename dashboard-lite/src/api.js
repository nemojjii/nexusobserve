// dashboard-lite talks only to the public Collector endpoints.
// /aggregate is a hosted-tier feature and is not called here.

const BASE = '/api'

async function _json(path, opts = {}) {
  const res = await fetch(BASE + path, opts)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${opts.method || 'GET'} ${path} → ${res.status}: ${text}`)
  }
  return res.json()
}

export const getRuns = () => _json('/runs')

export const getRunDecisions = (runId) =>
  _json(`/runs/${encodeURIComponent(runId)}/decisions`)

export const postReplay = (decisionId, alternativeAction) =>
  _json('/replay', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision_id: decisionId, alternative_action: alternativeAction }),
  })

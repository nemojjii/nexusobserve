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

export const getRunDecisions = (runId) => _json(`/runs/${encodeURIComponent(runId)}/decisions`)

export const getAggregate = () => _json('/aggregate')

export const postReplay = (decisionId, alternativeAction) =>
  _json('/replay', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision_id: decisionId, alternative_action: alternativeAction }),
  })

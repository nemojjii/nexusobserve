import React, { useCallback, useEffect, useRef, useState } from 'react'
import { getRunDecisions, getRuns, postReplay } from './api.js'
import DecisionGraph from './components/DecisionGraph.jsx'
import DiffPanel from './components/DiffPanel.jsx'
import SummaryBar from './components/SummaryBar.jsx'

const POLL_MS = 3000

const S = {
  root: { display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' },
  toolbar: {
    display: 'flex', alignItems: 'center', gap: 12, padding: '10px 20px',
    background: '#12151f', borderBottom: '1px solid #1e2235', flexShrink: 0,
  },
  label: { fontSize: 13, color: '#6c757d' },
  select: {
    background: '#1a1d2e', color: '#e8eaf0', border: '1px solid #2a2f45',
    borderRadius: 6, padding: '5px 10px', fontSize: 13, cursor: 'pointer',
  },
  body: { display: 'flex', flex: 1, overflow: 'hidden' },
  errorBanner: {
    padding: '8px 20px', background: '#2e1a1a', color: '#e74c3c',
    fontSize: 13, flexShrink: 0,
  },
}

export default function App() {
  const [runs, setRuns] = useState([])
  const [selectedRun, setSelectedRun] = useState('')
  const [decisions, setDecisions] = useState([])
  const [replayResult, setReplayResult] = useState(null)
  const [error, setError] = useState(null)
  const [replayLoading, setReplayLoading] = useState(false)
  const pollRef = useRef(null)

  const fetchDecisions = useCallback(async (runId) => {
    if (!runId) return
    try {
      const d = await getRunDecisions(runId)
      setDecisions(d.decisions || [])
    } catch (e) {
      setError(e.message)
    }
  }, [])

  const fetchRuns = useCallback(async () => {
    try {
      setError(null)
      const r = await getRuns()
      const list = r.runs || []
      setRuns(list)
      if (list.length && !selectedRun) {
        setSelectedRun(list[0])
        await fetchDecisions(list[0])
      } else if (selectedRun) {
        await fetchDecisions(selectedRun)
      }
    } catch (e) {
      setError(e.message)
    }
  }, [selectedRun, fetchDecisions])

  useEffect(() => { fetchRuns() }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    pollRef.current = setInterval(fetchRuns, POLL_MS)
    return () => clearInterval(pollRef.current)
  }, [fetchRuns])

  const handleRunChange = useCallback(async (e) => {
    const rid = e.target.value
    setSelectedRun(rid)
    setReplayResult(null)
    setDecisions([])
    if (rid) await fetchDecisions(rid)
  }, [fetchDecisions])

  const handleAlternativeClick = useCallback(async ({ decisionId, altAction }) => {
    setReplayLoading(true)
    setReplayResult(null)
    try {
      const result = await postReplay(decisionId, altAction)
      setReplayResult(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setReplayLoading(false)
    }
  }, [])

  return (
    <div style={S.root}>
      <SummaryBar decisions={decisions} runsCount={runs.length} />

      <div style={S.toolbar}>
        <span style={S.label}>런 선택</span>
        <select style={S.select} value={selectedRun} onChange={handleRunChange}>
          {runs.length === 0 && <option value="">— 데이터 없음 —</option>}
          {runs.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <span style={{ ...S.label, marginLeft: 8 }}>
          {decisions.length}개 결정 · 대안 클릭 → replay
        </span>
        {replayLoading && (
          <span style={{ fontSize: 12, color: '#4a9eff', marginLeft: 8 }}>⏳ replay 중…</span>
        )}
      </div>

      {error && <div style={S.errorBanner}>⚠️ {error}</div>}

      <div style={S.body}>
        <DecisionGraph decisions={decisions} onAlternativeClick={handleAlternativeClick} />
        {replayResult && (
          <DiffPanel result={replayResult} onClose={() => setReplayResult(null)} />
        )}
      </div>
    </div>
  )
}

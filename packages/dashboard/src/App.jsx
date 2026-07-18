import React, { useCallback, useEffect, useRef, useState } from 'react'
import { getAggregate, getRunDecisions, getRuns, postReplay } from './api.js'
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
    padding: '8px 20px', background: '#2e1a1a', color: '#e74c3c', fontSize: 13,
    flexShrink: 0,
  },
}

export default function App() {
  const [runs, setRuns] = useState([])
  const [selectedRun, setSelectedRun] = useState('')
  const [decisions, setDecisions] = useState([])
  const [aggregate, setAggregate] = useState(null)
  const [replayResult, setReplayResult] = useState(null)
  const [error, setError] = useState(null)
  const [replayLoading, setReplayLoading] = useState(false)

  const pollRef = useRef(null)

  const fetchData = useCallback(async (runId) => {
    try {
      setError(null)
      const [runsRes, aggRes] = await Promise.all([getRuns(), getAggregate()])
      const newRuns = runsRes.runs || []
      setRuns(newRuns)
      setAggregate(aggRes)

      // Auto-select first run if none selected
      const active = runId || (newRuns.length > 0 ? newRuns[0] : '')
      if (active && active !== selectedRun) setSelectedRun(active)
      if (active) {
        const dRes = await getRunDecisions(active)
        setDecisions(dRes.decisions || [])
      }
    } catch (e) {
      setError(e.message)
    }
  }, [selectedRun])

  // Initial load
  useEffect(() => {
    fetchData('')
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Poll every 3 s
  useEffect(() => {
    pollRef.current = setInterval(() => fetchData(selectedRun), POLL_MS)
    return () => clearInterval(pollRef.current)
  }, [selectedRun, fetchData])

  // Fetch decisions when run changes manually
  const handleRunChange = useCallback(async (e) => {
    const rid = e.target.value
    setSelectedRun(rid)
    setReplayResult(null)
    if (!rid) return
    try {
      const dRes = await getRunDecisions(rid)
      setDecisions(dRes.decisions || [])
    } catch (e) {
      setError(e.message)
    }
  }, [])

  // Called when user clicks an alternative node in the graph
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
      <SummaryBar aggregate={aggregate} />

      {/* Toolbar: run selector */}
      <div style={S.toolbar}>
        <span style={S.label}>런 선택</span>
        <select style={S.select} value={selectedRun} onChange={handleRunChange}>
          {runs.length === 0 && <option value="">— 데이터 없음 —</option>}
          {runs.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <span style={{ ...S.label, marginLeft: 8 }}>
          {decisions.length}개 결정 · 대안 클릭 시 replay 패널
        </span>
        {replayLoading && (
          <span style={{ fontSize: 12, color: '#4a9eff', marginLeft: 8 }}>
            ⏳ replay 중…
          </span>
        )}
      </div>

      {error && <div style={S.errorBanner}>⚠️ {error}</div>}

      {/* Main body: graph + diff panel */}
      <div style={S.body}>
        <DecisionGraph
          decisions={decisions}
          onAlternativeClick={handleAlternativeClick}
        />
        {replayResult && (
          <DiffPanel
            result={replayResult}
            onClose={() => setReplayResult(null)}
          />
        )}
      </div>
    </div>
  )
}

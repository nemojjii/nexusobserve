import React from 'react'

// Compute summary stats from the decisions array — no server aggregate needed.
function computeStats(decisions) {
  let totalChosen = 0
  let totalOpportunity = 0
  for (const d of decisions) {
    const chosen = d.chosen?.cost ?? 0
    totalChosen += chosen
    const altCosts = (d.alternatives || [])
      .map((a) => a.cost)
      .filter((c) => c != null)
    if (altCosts.length) {
      const savings = chosen - Math.min(...altCosts)
      if (savings > 0) totalOpportunity += savings
    }
  }
  return { totalChosen, totalOpportunity }
}

const S = {
  bar: {
    display: 'flex', alignItems: 'center', gap: 24,
    padding: '12px 24px', background: '#12151f',
    borderBottom: '1px solid #1e2235', flexShrink: 0,
  },
  logo: { fontWeight: 700, fontSize: 17, color: '#4a9eff', letterSpacing: 1 },
  chip: {
    display: 'inline-flex', alignItems: 'center', gap: 6,
    padding: '4px 12px', borderRadius: 20,
    background: '#1a1d2e', fontSize: 13, color: '#b0b8d0',
  },
  chipValue: { color: '#e8eaf0', fontWeight: 600 },
  dot: { width: 8, height: 8, borderRadius: '50%', background: '#27ae60' },
}

export default function SummaryBar({ decisions, runsCount }) {
  const { totalChosen, totalOpportunity } = computeStats(decisions)
  return (
    <div style={S.bar}>
      <span style={S.logo}>🔵 NEXUS</span>

      <span style={S.chip}>
        <span style={S.dot} />
        결정 <span style={S.chipValue}>{decisions.length}</span>건
      </span>

      <span style={S.chip}>
        누적 선택 비용
        <span style={S.chipValue}>${totalChosen.toFixed(0)}</span>
      </span>

      <span style={{ ...S.chip, background: '#1a2e1a' }}>
        💸 절감 가능
        <span style={{ ...S.chipValue, color: '#2ecc71' }}>
          ${totalOpportunity.toFixed(0)}
        </span>
      </span>

      <span style={{ ...S.chip, marginLeft: 'auto' }}>
        런 <span style={S.chipValue}>{runsCount}</span>개
      </span>
    </div>
  )
}

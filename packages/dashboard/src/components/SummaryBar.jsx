import React from 'react'

const S = {
  bar: {
    display: 'flex', alignItems: 'center', gap: 24,
    padding: '12px 24px', background: '#12151f',
    borderBottom: '1px solid #1e2235',
    flexShrink: 0,
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

export default function SummaryBar({ aggregate }) {
  const a = aggregate || {}
  return (
    <div style={S.bar}>
      <span style={S.logo}>🔵 NEXUS</span>

      <span style={S.chip}>
        <span style={S.dot} />
        결정 <span style={S.chipValue}>{a.total_decisions ?? '—'}</span>건
      </span>

      <span style={S.chip}>
        누적 선택 비용
        <span style={S.chipValue}>
          {a.total_chosen_cost != null ? `$${a.total_chosen_cost.toFixed(0)}` : '—'}
        </span>
      </span>

      <span style={{ ...S.chip, background: '#1a2e1a' }}>
        💸 절감 가능
        <span style={{ ...S.chipValue, color: '#2ecc71' }}>
          {a.total_opportunity_cost != null
            ? `$${a.total_opportunity_cost.toFixed(0)}`
            : '—'}
        </span>
      </span>

      <span style={{ ...S.chip, marginLeft: 'auto' }}>
        실행 {a.runs_count ?? '—'}개 런
      </span>
    </div>
  )
}

import React from 'react'

const S = {
  panel: {
    width: 340, flexShrink: 0,
    background: '#12151f', borderLeft: '1px solid #1e2235',
    padding: 20, overflowY: 'auto',
    display: 'flex', flexDirection: 'column', gap: 16,
  },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  },
  title: { fontSize: 14, fontWeight: 700, color: '#b0b8d0' },
  closeBtn: {
    background: 'none', border: 'none', cursor: 'pointer',
    color: '#6c757d', fontSize: 18, lineHeight: 1,
  },
  diffCard: {
    background: '#1a1d2e', borderRadius: 8, padding: '14px 16px',
  },
  label: { fontSize: 11, color: '#6c757d', textTransform: 'uppercase', letterSpacing: 0.8 },
  valueLarge: { fontSize: 28, fontWeight: 700, marginTop: 4 },
  safer: {
    display: 'inline-flex', alignItems: 'center', gap: 6,
    padding: '6px 14px', borderRadius: 20,
    background: '#1a2e1a', border: '1px solid #27ae60',
    color: '#2ecc71', fontWeight: 700, fontSize: 13,
  },
  dangerBadge: {
    display: 'inline-flex', alignItems: 'center', gap: 6,
    padding: '6px 14px', borderRadius: 20,
    background: '#2e1a1a', border: '1px solid #e74c3c',
    color: '#e74c3c', fontWeight: 700, fontSize: 13,
  },
  toolRow: {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '8px 0', borderBottom: '1px solid #1e2235', fontSize: 13,
  },
  toolBadge: (status) => ({
    padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
    background: status === 'REPLAYED' ? '#1a2840' : '#2e1a1a',
    color: status === 'REPLAYED' ? '#4a9eff' : '#e74c3c',
  }),
  tradeoffRow: {
    display: 'flex', justifyContent: 'space-between',
    padding: '6px 0', fontSize: 13, color: '#b0b8d0',
    borderBottom: '1px solid #1e2235',
  },
}

function CostDelta({ delta }) {
  if (delta == null) return <span style={{ color: '#6c757d' }}>비교 불가</span>
  const cheaper = delta > 0
  return (
    <div>
      <div style={S.label}>비용 절감 (cost_delta)</div>
      <div style={{ ...S.valueLarge, color: cheaper ? '#2ecc71' : '#e74c3c' }}>
        {cheaper ? '−' : '+'}${Math.abs(delta).toFixed(2)}
      </div>
      <div style={{ fontSize: 12, color: '#6c757d', marginTop: 4 }}>
        {cheaper
          ? `선택 대안보다 $${Math.abs(delta).toFixed(2)} 저렴`
          : `선택 대안보다 $${Math.abs(delta).toFixed(2)} 비쌈`}
      </div>
    </div>
  )
}

export default function DiffPanel({ result, onClose }) {
  if (!result) return null

  const {
    original_action, replayed_action, cost_delta,
    side_effects_executed, replayed_tools = [], tradeoffs = {},
  } = result

  const tradeoffEntries = Object.entries(tradeoffs).filter(
    ([k]) => !k.startsWith('alt_') || k === 'alt_reason'
  )

  return (
    <div style={S.panel}>
      {/* header */}
      <div style={S.header}>
        <span style={S.title}>Replay Diff</span>
        <button style={S.closeBtn} onClick={onClose} aria-label="닫기">✕</button>
      </div>

      {/* actions */}
      <div style={{ fontSize: 13, color: '#6c757d' }}>
        <span style={{ color: '#e74c3c', fontWeight: 600 }}>{original_action}</span>
        {' '} 대신{' '}
        <span style={{ color: '#4a9eff', fontWeight: 600 }}>{replayed_action}</span>
        {' '}을 선택했다면
      </div>

      {/* cost delta */}
      <div style={S.diffCard}>
        <CostDelta delta={cost_delta} />
      </div>

      {/* safety badge */}
      <div>
        {side_effects_executed === 0 ? (
          <span style={S.safer}>✅ 안전: 실제 실행 {side_effects_executed}건</span>
        ) : (
          <span style={S.dangerBadge}>⚠️ 사이드이펙트 {side_effects_executed}건 실행됨</span>
        )}
      </div>

      {/* tools */}
      {replayed_tools.length > 0 && (
        <div>
          <div style={{ ...S.label, marginBottom: 8 }}>도구 재실행</div>
          {replayed_tools.map((t, i) => (
            <div key={i} style={S.toolRow}>
              <span style={S.toolBadge(t.status)}>{t.status}</span>
              <span style={{ flex: 1, color: '#e8eaf0' }}>{t.tool}</span>
              {t.status === 'SIMULATED' && (
                <span style={{ fontSize: 11, color: '#e74c3c' }}>미실행</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* tradeoffs */}
      {tradeoffEntries.length > 0 && (
        <div>
          <div style={{ ...S.label, marginBottom: 8 }}>기타 트레이드오프</div>
          {tradeoffEntries.map(([k, v]) => (
            <div key={k} style={S.tradeoffRow}>
              <span>{k}</span>
              <span style={{ color: '#e8eaf0', fontWeight: 500 }}>
                {typeof v === 'number' ? v.toLocaleString() : String(v)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

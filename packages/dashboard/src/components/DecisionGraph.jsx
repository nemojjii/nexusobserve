import React, { useCallback, useEffect, useRef, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'

// ── helpers ──────────────────────────────────────────────────────────────────

function nodeColor(node) {
  if (node.type === 'decision') return '#4a9eff'
  if (node.type === 'chosen') return '#27ae60'
  return '#6c757d'
}

function nodeRadius(node) {
  if (node.type === 'chosen') return 16
  if (node.type === 'decision') return 13
  return 9
}

function buildGraphData(decisions) {
  const nodes = []
  const links = []

  decisions.forEach((d) => {
    const did = d.decision_id
    const orderId = d.context?.order_id || d.run_id || did.slice(0, 8)

    nodes.push({
      id: did,
      type: 'decision',
      label: orderId,
      val: 5,
      data: d,
    })

    // chosen child
    const chosenId = `${did}:chosen`
    nodes.push({
      id: chosenId,
      type: 'chosen',
      label: `${d.chosen?.action ?? '?'}\n$${d.chosen?.cost ?? '?'}`,
      val: 8,
      data: d,
    })
    links.push({ source: did, target: chosenId })

    // alternative children
    ;(d.alternatives || []).forEach((alt) => {
      const altId = `${did}:alt:${alt.action}`
      nodes.push({
        id: altId,
        type: 'alternative',
        label: `${alt.action}\n$${alt.cost}`,
        val: 2,
        data: d,
        altAction: alt.action,
        decisionId: did,
      })
      links.push({ source: did, target: altId })
    })
  })

  return { nodes, links }
}

// Custom canvas drawing for a node
function paintNode(node, ctx, globalScale) {
  const r = nodeRadius(node)
  const isAlt = node.type === 'alternative'

  // Circle
  ctx.beginPath()
  ctx.arc(node.x, node.y, r, 0, 2 * Math.PI)
  ctx.fillStyle = isAlt ? '#3a3f50' : nodeColor(node)
  ctx.fill()

  if (!isAlt) {
    ctx.strokeStyle = nodeColor(node)
    ctx.lineWidth = 2
    ctx.stroke()
  } else {
    ctx.strokeStyle = '#6c757d'
    ctx.lineWidth = 1.5
    ctx.stroke()
  }

  // Label(s) — split on \n
  const lines = (node.label || '').split('\n')
  const fontSize = Math.max(9, 11 / globalScale)
  ctx.font = `${node.type === 'chosen' ? '700 ' : ''}${fontSize}px -apple-system,sans-serif`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  ctx.fillStyle = isAlt ? 'rgba(180,185,210,0.75)' : '#ffffff'

  lines.forEach((line, i) => {
    ctx.fillText(line, node.x, node.y + r + 4 + i * (fontSize + 2))
  })
}

// ── component ─────────────────────────────────────────────────────────────────

export default function DecisionGraph({ decisions, onAlternativeClick }) {
  const fgRef = useRef()
  const containerRef = useRef()
  const [dims, setDims] = useState({ w: 800, h: 600 })
  const [graphData, setGraphData] = useState({ nodes: [], links: [] })

  // Rebuild graph whenever decisions change
  useEffect(() => {
    setGraphData(buildGraphData(decisions))
  }, [decisions])

  // Tune forces after graphData update
  useEffect(() => {
    if (!fgRef.current) return
    fgRef.current.d3Force('charge').strength(-300)
    fgRef.current.d3Force('link').distance(90)
  }, [graphData])

  // Track container size
  useEffect(() => {
    if (!containerRef.current) return
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) {
        setDims({ w: e.contentRect.width, h: e.contentRect.height })
      }
    })
    ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [])

  const handleNodeClick = useCallback(
    (node) => {
      if (node.type === 'alternative') {
        onAlternativeClick({ decisionId: node.decisionId, altAction: node.altAction })
      }
    },
    [onAlternativeClick]
  )

  const handleNodeHover = useCallback((node) => {
    document.body.style.cursor = node?.type === 'alternative' ? 'pointer' : 'default'
  }, [])

  // Empty-state
  if (decisions.length === 0) {
    return (
      <div
        ref={containerRef}
        style={{
          flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#3a3f50', fontSize: 15,
        }}
      >
        결정 데이터가 없습니다. 런을 선택하거나 에이전트를 실행하세요.
      </div>
    )
  }

  return (
    <div ref={containerRef} style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
      <ForceGraph2D
        ref={fgRef}
        graphData={graphData}
        width={dims.w}
        height={dims.h}
        backgroundColor="#0f1117"
        nodeCanvasObjectMode={() => 'replace'}
        nodeCanvasObject={paintNode}
        nodePointerAreaPaint={(node, color, ctx) => {
          ctx.beginPath()
          ctx.arc(node.x, node.y, nodeRadius(node) + 6, 0, 2 * Math.PI)
          ctx.fillStyle = color
          ctx.fill()
        }}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        linkColor={() => '#1e2235'}
        linkWidth={1.5}
        enableNodeDrag={true}
        enableZoomInteraction={true}
      />

      {/* Legend */}
      <div style={{
        position: 'absolute', bottom: 16, left: 16,
        display: 'flex', gap: 12, fontSize: 12, color: '#6c757d',
        background: 'rgba(15,17,23,0.85)', padding: '8px 14px', borderRadius: 8,
      }}>
        <span><Circle color="#4a9eff" /> 결정</span>
        <span><Circle color="#27ae60" /> 선택됨</span>
        <span><Circle color="#3a3f50" border="#6c757d" /> 대안 (클릭 가능)</span>
      </div>
    </div>
  )
}

function Circle({ color, border }) {
  return (
    <span style={{
      display: 'inline-block', width: 10, height: 10, borderRadius: '50%',
      background: color, border: border ? `1.5px solid ${border}` : 'none',
      verticalAlign: 'middle', marginRight: 4,
    }} />
  )
}

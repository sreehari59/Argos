export default function GraphView() {
  return (
    <div>
      <h1 style={{ marginBottom: '1.5rem' }}>Interactive Knowledge Graph</h1>
      
      <div className="card" style={{ padding: '1rem' }}>
        <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>
          Explore the full supply chain network with our enhanced interactive visualization.
        </p>
        <iframe 
          src="/new-graph/knowledge-graph.html"
          style={{ 
            width: '100%', 
            height: '800px', 
            border: '1px solid var(--border)',
            borderRadius: '8px',
            background: '#0a0e1a'
          }}
          title="Supply Chain Knowledge Graph"
        />
        <div style={{ marginTop: '1rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
          <p><strong>Features:</strong></p>
          <ul style={{ marginLeft: '1.5rem', marginTop: '0.5rem' }}>
            <li>Interactive force-directed graph with D3.js</li>
            <li>Filter by node type (companies, products, ingredients, suppliers)</li>
            <li>Search functionality to find specific entities</li>
            <li>Click nodes to view detailed information and connections</li>
            <li>Zoom and pan to explore different areas</li>
            <li>Real-time insights and network statistics</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

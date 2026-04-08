import { useState, useEffect } from 'react'

const API_BASE = 'http://localhost:8000/api'

export default function RecommendationsView() {
  const [topRecs, setTopRecs] = useState([])
  const [consolidation, setConsolidation] = useState([])
  const [filter, setFilter] = useState('all')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  useEffect(() => {
    fetch(`${API_BASE}/recommendations/top?limit=50`)
      .then(res => res.json())
      .then(data => setTopRecs(data))
      .catch(err => console.error('Failed to load recommendations:', err))

    fetch(`${API_BASE}/recommendations/consolidation`)
      .then(res => res.json())
      .then(data => setConsolidation(data))
      .catch(err => console.error('Failed to load consolidation:', err))
  }, [])

  const filteredRecs = filter === 'all' 
    ? topRecs 
    : topRecs.filter(r => r.family_type === filter)

  // Reset to page 1 when filter changes
  useEffect(() => {
    setCurrentPage(1)
  }, [filter])

  // Pagination calculations
  const totalPages = Math.ceil(filteredRecs.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const currentRecs = filteredRecs.slice(startIndex, endIndex)

  const goToPage = (page) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)))
  }

  return (
    <div>
      <h1 style={{ marginBottom: '2rem' }}>Substitution Recommendations</h1>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2>🎯 Top Recommendations ({filteredRecs.length})</h2>
          <div>
            <button 
              className={`btn ${filter === 'all' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFilter('all')}
              style={{ marginRight: '0.5rem' }}
            >
              All
            </button>
            <button 
              className={`btn ${filter === 'form_variant' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFilter('form_variant')}
              style={{ marginRight: '0.5rem' }}
            >
              Form Variants
            </button>
            <button 
              className={`btn ${filter === 'functional_substitute' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFilter('functional_substitute')}
            >
              Functional Substitutes
            </button>
          </div>
        </div>

        {filteredRecs.length > 0 ? (
          <>
            <table className="table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Product</th>
                  <th>Current Ingredient</th>
                  <th>Substitute</th>
                  <th>Role</th>
                  <th>Type</th>
                  <th>Score</th>
                  <th>Suppliers</th>
                </tr>
              </thead>
              <tbody>
                {currentRecs.map((rec, idx) => (
                  <tr key={idx}>
                    <td>{rec.company_name}</td>
                    <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {rec.product_sku}
                    </td>
                    <td>{rec.current_canonical_name}</td>
                    <td style={{ color: 'var(--success)', fontWeight: '500' }}>
                      {rec.substitute_canonical_name}
                    </td>
                    <td>
                      <span className="badge badge-success">{rec.functional_role}</span>
                    </td>
                    <td>
                      <span className={`badge ${rec.family_type === 'form_variant' ? 'badge-success' : 'badge-warning'}`}>
                        {rec.family_type}
                      </span>
                    </td>
                    <td style={{ fontWeight: 'bold' }}>{rec.final_score.toFixed(3)}</td>
                    <td style={{ fontSize: '0.75rem' }}>
                      {rec.available_suppliers.slice(0, 2).join(', ')}
                      {rec.available_suppliers.length > 2 && ` +${rec.available_suppliers.length - 2}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', marginTop: '1.5rem', paddingBottom: '1rem' }}>
                <button 
                  className="btn btn-secondary"
                  onClick={() => goToPage(currentPage - 1)}
                  disabled={currentPage === 1}
                  style={{ opacity: currentPage === 1 ? 0.5 : 1, cursor: currentPage === 1 ? 'not-allowed' : 'pointer' }}
                >
                  ← Previous
                </button>
                
                <div style={{ display: 'flex', gap: '0.25rem' }}>
                  {[...Array(totalPages)].map((_, i) => {
                    const page = i + 1
                    // Show first, last, current, and adjacent pages
                    if (page === 1 || page === totalPages || (page >= currentPage - 1 && page <= currentPage + 1)) {
                      return (
                        <button
                          key={page}
                          className={`btn ${page === currentPage ? 'btn-primary' : 'btn-secondary'}`}
                          onClick={() => goToPage(page)}
                          style={{ minWidth: '40px' }}
                        >
                          {page}
                        </button>
                      )
                    } else if (page === currentPage - 2 || page === currentPage + 2) {
                      return <span key={page} style={{ padding: '0.5rem', color: 'var(--text-muted)' }}>...</span>
                    }
                    return null
                  })}
                </div>

                <button 
                  className="btn btn-secondary"
                  onClick={() => goToPage(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  style={{ opacity: currentPage === totalPages ? 0.5 : 1, cursor: currentPage === totalPages ? 'not-allowed' : 'pointer' }}
                >
                  Next →
                </button>
              </div>
            )}

            <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', textAlign: 'center', marginTop: '1rem', paddingBottom: '1rem' }}>
              Showing {startIndex + 1}-{Math.min(endIndex, filteredRecs.length)} of {filteredRecs.length} recommendations
            </div>

            {/* Methodology Explanation */}
            <div style={{ 
              marginTop: '1.5rem', 
              padding: '1rem', 
              background: 'var(--bg-card)', 
              borderRadius: '8px', 
              border: '1px solid var(--border)',
              fontSize: '0.875rem',
              lineHeight: '1.6'
            }}>
              <h3 style={{ fontSize: '0.9rem', marginBottom: '0.75rem', color: 'var(--text-secondary)', fontWeight: '600' }}>
                📊 How Recommendations Are Calculated
              </h3>
              <p style={{ color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                Our AI-powered recommendation engine analyzes your supply chain using a <strong>3-factor scoring system</strong>:
              </p>
              <ul style={{ marginLeft: '1.5rem', color: 'var(--text-muted)' }}>
                <li><strong>Quality Score (0-1):</strong> Evaluates ingredient quality based on form variants vs. functional substitutes. Form variants (e.g., "vitamin D3" → "cholecalciferol") score higher as they're chemically identical.</li>
                <li><strong>Compliance Score (0-1):</strong> Assesses regulatory compliance and certifications (organic, non-GMO, kosher, halal) to ensure substitutes meet your standards.</li>
                <li><strong>Priority Rank (0-1):</strong> Considers ingredient position in formulation labels - higher priority for ingredients listed first (indicating higher proportion).</li>
              </ul>
              <p style={{ color: 'var(--text-muted)', marginTop: '0.75rem' }}>
                <strong>Final Score = </strong> (Quality × 0.4) + (Compliance × 0.3) + (Priority × 0.3)
              </p>
              <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem', fontSize: '0.8125rem', fontStyle: 'italic' }}>
                Data sourced from ingredient family matching, functional role analysis, and supplier availability across {topRecs.length > 0 ? '149 products' : 'your product catalog'}.
              </p>
            </div>
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>🔍</div>
            <h3>No Recommendations Available</h3>
            <p style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>
              The recommendation pipeline needs to be run to generate substitution candidates.
            </p>
            <p style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: 'var(--text-dim)' }}>
              Run: <code style={{ background: 'var(--bg-card)', padding: '0.25rem 0.5rem', borderRadius: '4px' }}>python recommendations.py</code>
            </p>
          </div>
        )}
      </div>

      <div className="card">
        <h2>🔗 Supplier Consolidation Opportunities</h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
          Opportunities to reduce supplier count by switching to substitutes available from fewer suppliers.
        </p>
        <table className="table">
          <thead>
            <tr>
              <th>Company</th>
              <th>Target Supplier</th>
              <th>Substitutions</th>
              <th>Avg Score</th>
            </tr>
          </thead>
          <tbody>
            {consolidation.slice(0, 15).map((opp, idx) => (
              <tr key={idx}>
                <td>{opp.company_name}</td>
                <td style={{ fontWeight: '500' }}>{opp.supplier_name}</td>
                <td>
                  <span className="badge badge-success">{opp.substitution_count}</span>
                </td>
                <td>{opp.avg_score.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

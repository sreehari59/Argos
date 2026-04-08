import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

const API_BASE = 'http://localhost:8000/api'

export default function Recommendations() {
  const [recommendations, setRecommendations] = useState([])
  const [consolidation, setConsolidation] = useState([])
  const [filter, setFilter] = useState('all')
  const [sortBy, setSortBy] = useState('score')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/recommendations/top?limit=100`).then(res => res.json()),
      fetch(`${API_BASE}/recommendations/consolidation`).then(res => res.json())
    ])
      .then(([recs, cons]) => {
        setRecommendations(recs)
        setConsolidation(cons)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to load:', err)
        setLoading(false)
      })
  }, [])

  const filteredRecs = recommendations
    .filter(r => filter === 'all' || r.family_type === filter)
    .sort((a, b) => {
      if (sortBy === 'score') return b.final_score - a.final_score
      if (sortBy === 'company') return a.company_name.localeCompare(b.company_name)
      return 0
    })

  const stats = {
    total: recommendations.length,
    formVariants: recommendations.filter(r => r.family_type === 'form_variant').length,
    functionalSubs: recommendations.filter(r => r.family_type === 'functional_substitute').length,
    avgScore: recommendations.length > 0 
      ? (recommendations.reduce((sum, r) => sum + r.final_score, 0) / recommendations.length).toFixed(3)
      : '0.000'
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading recommendations...</p>
      </div>
    )
  }

  return (
    <div className="recommendations-page">
      {/* Hero Section */}
      <div className="page-hero">
        <div className="hero-content">
          <div className="hero-badge">AI-Powered Intelligence</div>
          <h1 className="hero-title">
            Smart Substitution
            <span className="gradient-text"> Recommendations</span>
          </h1>
          <p className="hero-description">
            Discover better alternatives for your raw materials while maintaining compliance,
            quality, and formulation integrity. Every recommendation is scored on compliance,
            quality, and ingredient priority.
          </p>
        </div>
        
        <div className="hero-stats">
          <div className="hero-stat">
            <div className="stat-number">{stats.total}</div>
            <div className="stat-label">Total Opportunities</div>
          </div>
          <div className="hero-stat">
            <div className="stat-number">{stats.avgScore}</div>
            <div className="stat-label">Average Score</div>
          </div>
          <div className="hero-stat">
            <div className="stat-number">{stats.formVariants}</div>
            <div className="stat-label">Form Variants</div>
          </div>
        </div>
      </div>

      {/* Filter Controls */}
      <div className="filter-section">
        <div className="filter-group">
          <label className="filter-label">Filter by Type</label>
          <div className="filter-buttons">
            <button 
              className={`filter-chip ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              <span className="chip-icon">●</span>
              All ({stats.total})
            </button>
            <button 
              className={`filter-chip ${filter === 'form_variant' ? 'active' : ''}`}
              onClick={() => setFilter('form_variant')}
            >
              <span className="chip-icon">◆</span>
              Form Variants ({stats.formVariants})
            </button>
            <button 
              className={`filter-chip ${filter === 'functional_substitute' ? 'active' : ''}`}
              onClick={() => setFilter('functional_substitute')}
            >
              <span className="chip-icon">◇</span>
              Functional Substitutes ({stats.functionalSubs})
            </button>
          </div>
        </div>

        <div className="filter-group">
          <label className="filter-label">Sort by</label>
          <select 
            className="sort-select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="score">Highest Score</option>
            <option value="company">Company Name</option>
          </select>
        </div>
      </div>

      {/* Recommendations Grid */}
      <div className="recommendations-grid">
        {filteredRecs.slice(0, 50).map((rec, idx) => (
          <div key={idx} className="recommendation-card">
            <div className="card-header">
              <div className="card-meta">
                <Link to={`/company/${rec.company_id}`} className="company-link">
                  {rec.company_name}
                </Link>
                <span className="product-sku">{rec.product_sku}</span>
              </div>
              <div className="score-badge">
                <div className="score-value">{rec.final_score.toFixed(3)}</div>
                <div className="score-label">Score</div>
              </div>
            </div>

            <div className="substitution-flow">
              <div className="ingredient-box current">
                <div className="ingredient-label">Current</div>
                <div className="ingredient-name">{rec.current_canonical_name}</div>
              </div>
              
              <div className="flow-arrow">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path d="M5 12h14m-6-6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>

              <div className="ingredient-box substitute">
                <div className="ingredient-label">Substitute</div>
                <div className="ingredient-name">{rec.substitute_canonical_name}</div>
              </div>
            </div>

            <div className="card-details">
              <div className="detail-row">
                <span className="detail-label">Role</span>
                <span className="role-badge">{rec.functional_role}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Type</span>
                <span className={`type-badge ${rec.family_type === 'form_variant' ? 'variant' : 'functional'}`}>
                  {rec.family_type === 'form_variant' ? 'Form Variant' : 'Functional Substitute'}
                </span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Suppliers</span>
                <span className="suppliers-list">
                  {rec.available_suppliers.slice(0, 2).join(', ')}
                  {rec.available_suppliers.length > 2 && ` +${rec.available_suppliers.length - 2} more`}
                </span>
              </div>
            </div>

            {rec.compliance_reasoning && (
              <div className="reasoning-section">
                <div className="reasoning-label">✓ Compliance</div>
                <p className="reasoning-text">{rec.compliance_reasoning}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Consolidation Opportunities */}
      {consolidation.length > 0 && (
        <div className="consolidation-section">
          <div className="section-header">
            <h2>Supplier Consolidation Opportunities</h2>
            <p className="section-description">
              Reduce supplier complexity by consolidating multiple ingredients with fewer suppliers
            </p>
          </div>

          <div className="consolidation-grid">
            {consolidation.slice(0, 12).map((opp, idx) => (
              <div key={idx} className="consolidation-card">
                <div className="consolidation-header">
                  <div className="company-name">{opp.company_name}</div>
                  <div className="consolidation-count">{opp.substitution_count} substitutions</div>
                </div>
                <div className="supplier-name">→ {opp.supplier_name}</div>
                <div className="consolidation-score">
                  Avg Score: <strong>{opp.avg_score.toFixed(3)}</strong>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

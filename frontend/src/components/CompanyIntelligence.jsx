import { useState, useEffect } from 'react'

const API_BASE = 'http://localhost:8000/api'

export default function CompanyIntelligence({ companyId, onBack }) {
  const [company, setCompany] = useState(null)
  const [healthScore, setHealthScore] = useState(null)
  const [batchingOpps, setBatchingOpps] = useState([])
  const [recommendations, setRecommendations] = useState([])
  const [selectedAction, setSelectedAction] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)

    Promise.all([
      fetch(`${API_BASE}/companies/${companyId}`).then(res => res.json()),
      fetch(`${API_BASE}/analytics/company/${companyId}/health`).then(res => res.json()),
      fetch(`${API_BASE}/analytics/batching?company_id=${companyId}`).then(res => res.json()),
      fetch(`${API_BASE}/recommendations/diversification/${companyId}`).then(res => res.json())
    ])
      .then(([companyData, healthData, batchingData, recsData]) => {
        setCompany(companyData)
        setHealthScore(healthData)
        setBatchingOpps(batchingData.filter(b => b.company_id === companyId))
        setRecommendations(recsData.recommendations || [])
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to load company intelligence:', err)
        setError('Failed to load company data. Please try again.')
        setLoading(false)
      })
  }, [companyId])

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading company intelligence...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚠️</div>
          <h3>{error}</h3>
          <button className="btn btn-primary" onClick={onBack} style={{ marginTop: '1rem' }}>
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  if (!company || !healthScore) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <p>No data available for this company.</p>
          <button className="btn btn-primary" onClick={onBack} style={{ marginTop: '1rem' }}>
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  const getGradeColor = (grade) => {
    switch(grade) {
      case 'A': return 'var(--success)'
      case 'B': return 'var(--primary-light)'
      case 'C': return 'var(--warning)'
      case 'D': return 'var(--danger)'
      default: return 'var(--text-muted)'
    }
  }

  const priorityActions = []
  
  // Risk reduction actions
  if (healthScore.metrics.single_source_ingredients > 0) {
    priorityActions.push({
      type: 'risk',
      priority: 'HIGH',
      title: 'Reduce Single-Source Risk',
      description: `${healthScore.metrics.single_source_ingredients} ingredients from only 1 supplier`,
      impact: `-${Math.round(healthScore.metrics.single_source_percentage)}% supply chain risk`,
      action: 'diversify',
      count: healthScore.metrics.single_source_ingredients
    })
  }

  // Quality upgrade actions
  if (healthScore.metrics.quality_upgrade_opportunities > 0) {
    priorityActions.push({
      type: 'quality',
      priority: 'MEDIUM',
      title: 'Quality Upgrades Available',
      description: `${healthScore.metrics.quality_upgrade_opportunities} organic/non-GMO alternatives found`,
      impact: 'Premium positioning opportunity',
      action: 'upgrade',
      count: healthScore.metrics.quality_upgrade_opportunities
    })
  }

  // Batching consolidation actions
  if (batchingOpps.length > 0) {
    const topBatching = batchingOpps[0]
    priorityActions.push({
      type: 'consolidation',
      priority: 'MEDIUM',
      title: 'Supplier Consolidation',
      description: `Can batch ${topBatching.batching_benefit} ingredients with ${topBatching.recommended_supplier}`,
      impact: 'Estimated 8-12% procurement savings',
      action: 'consolidate',
      count: batchingOpps.length
    })
  }

  return (
    <div className="company-intelligence">
      <button className="btn btn-secondary" onClick={onBack} style={{ marginBottom: '1.5rem' }}>
        ← Back to Dashboard
      </button>

      {/* Company Header with Health Score */}
      <div className="company-header">
        <div className="company-info">
          <h1>{company.Name}</h1>
          <p className="company-subtitle">Supply Chain Intelligence Dashboard</p>
        </div>
        
        <div className="health-score-widget">
          <div className="health-score-circle" style={{ borderColor: getGradeColor(healthScore.grade) }}>
            <div className="score-value">{healthScore.overall_score}</div>
            <div className="score-max">/100</div>
          </div>
          <div className="health-score-details">
            <div className="score-grade" style={{ color: getGradeColor(healthScore.grade) }}>
              Grade {healthScore.grade}
            </div>
            <div className="score-label">Supply Chain Health</div>
          </div>
        </div>
      </div>

      {/* Priority Actions Panel */}
      {priorityActions.length > 0 && (
        <div className="card priority-actions-card">
          <h2>🎯 Priority Actions This Quarter</h2>
          <div className="priority-actions-grid">
            {priorityActions.map((action, idx) => (
              <div 
                key={idx} 
                className={`priority-action-item ${action.priority.toLowerCase()}`}
                onClick={() => setSelectedAction(action)}
              >
                <div className="action-header">
                  <span className={`priority-badge ${action.priority.toLowerCase()}`}>
                    {action.priority}
                  </span>
                  <span className="action-count">{action.count} opportunities</span>
                </div>
                <h3>{action.title}</h3>
                <p className="action-description">{action.description}</p>
                <div className="action-impact">
                  <span className="impact-icon">
                    {action.type === 'risk' ? '🛡️' : action.type === 'quality' ? '⭐' : '💰'}
                  </span>
                  {action.impact}
                </div>
                <button className="action-button">View Details →</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Health Score Breakdown */}
      <div className="card">
        <h2>📊 Supply Chain Health Breakdown</h2>
        <div className="health-metrics-grid">
          <div className="health-metric">
            <div className="metric-label">Single-Source Risk</div>
            <div className="metric-bar-container">
              <div 
                className="metric-bar" 
                style={{ 
                  width: `${healthScore.scores.single_source_risk}%`,
                  background: healthScore.scores.single_source_risk >= 70 ? 'var(--success)' : 'var(--warning)'
                }}
              ></div>
            </div>
            <div className="metric-value">{healthScore.scores.single_source_risk}/100</div>
            <div className="metric-detail">
              {healthScore.metrics.single_source_ingredients} of {healthScore.metrics.total_ingredients} ingredients
            </div>
          </div>

          <div className="health-metric">
            <div className="metric-label">Supplier Concentration</div>
            <div className="metric-bar-container">
              <div 
                className="metric-bar" 
                style={{ 
                  width: `${healthScore.scores.supplier_concentration}%`,
                  background: healthScore.scores.supplier_concentration >= 70 ? 'var(--success)' : 'var(--warning)'
                }}
              ></div>
            </div>
            <div className="metric-value">{healthScore.scores.supplier_concentration}/100</div>
            <div className="metric-detail">
              Top supplier: {healthScore.metrics.top_supplier_concentration}% concentration
            </div>
          </div>

          <div className="health-metric">
            <div className="metric-label">Supplier Diversification</div>
            <div className="metric-bar-container">
              <div 
                className="metric-bar" 
                style={{ 
                  width: `${healthScore.scores.supplier_diversification}%`,
                  background: 'var(--primary)'
                }}
              ></div>
            </div>
            <div className="metric-value">{healthScore.scores.supplier_diversification}/100</div>
            <div className="metric-detail">
              {healthScore.metrics.total_suppliers} suppliers in network
            </div>
          </div>
        </div>
      </div>

      {/* Batching Opportunities */}
      {batchingOpps.length > 0 && (
        <div className="card">
          <h2>💰 Supplier Batching Opportunities</h2>
          <p className="card-description">
            Consolidate procurement to reduce complexity and unlock volume discounts
          </p>
          <div className="batching-grid">
            {batchingOpps.slice(0, 6).map((opp, idx) => (
              <div key={idx} className="batching-card">
                <div className="batching-header">
                  <div className="ingredient-name">{opp.ingredient}</div>
                  <div className="batching-benefit-badge">
                    +{opp.batching_benefit} ingredients
                  </div>
                </div>
                <div className="batching-flow">
                  <div className="current-supplier">
                    <div className="supplier-label">Current</div>
                    <div className="supplier-name">{opp.current_supplier}</div>
                  </div>
                  <div className="arrow">→</div>
                  <div className="recommended-supplier">
                    <div className="supplier-label">Recommended</div>
                    <div className="supplier-name">{opp.recommended_supplier}</div>
                  </div>
                </div>
                <div className="batching-reason">{opp.reason}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Diversification Opportunities */}
      <div className="card">
        <h2>🔄 Diversification Opportunities</h2>
        {recommendations.length > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th>Ingredient</th>
                <th>Role</th>
                <th>Current Supplier</th>
                <th>Alternatives</th>
              </tr>
            </thead>
            <tbody>
              {recommendations.slice(0, 10).map((rec, idx) => (
                <tr key={idx}>
                  <td>{rec.ingredient}</td>
                  <td><span className="badge badge-success">{rec.role}</span></td>
                  <td>{rec.current_supplier}</td>
                  <td>
                    {rec.alternatives.map((alt, i) => (
                      <div key={i} style={{ fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                        <strong>{alt.substitute}</strong> ({alt.score.toFixed(2)})
                        <br />
                        <span style={{ color: 'var(--text-muted)' }}>
                          {alt.suppliers.join(', ')}
                        </span>
                      </div>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>✅</div>
            <p>No diversification opportunities found.</p>
            <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
              This company has good supplier diversification, or the recommendation pipeline needs to be run.
            </p>
          </div>
        )}
      </div>

      {/* Company Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{company.products.length}</div>
          <div className="stat-label">Products</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{company.ingredients.length}</div>
          <div className="stat-label">Unique Ingredients</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{company.suppliers.length}</div>
          <div className="stat-label">Suppliers</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{company.single_source_risks.length}</div>
          <div className="stat-label">Single-Source Risks</div>
        </div>
      </div>

      {/* Action Details Modal */}
      {selectedAction && (
        <div className="modal-overlay" onClick={() => setSelectedAction(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{selectedAction.title}</h2>
              <button className="modal-close" onClick={() => setSelectedAction(null)}>×</button>
            </div>
            <div className="modal-body">
              <div style={{ marginBottom: '1rem' }}>
                <span className={`priority-badge ${selectedAction.priority.toLowerCase()}`}>
                  {selectedAction.priority} PRIORITY
                </span>
              </div>
              <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>{selectedAction.description}</p>
              
              <div className="action-impact" style={{ padding: '1rem', background: 'var(--card-bg)', borderRadius: '8px', marginBottom: '1.5rem' }}>
                <strong>Expected Impact:</strong>
                <div style={{ marginTop: '0.5rem', fontSize: '1.1rem' }}>
                  <span className="impact-icon" style={{ marginRight: '0.5rem' }}>
                    {selectedAction.type === 'risk' ? '🛡️' : selectedAction.type === 'quality' ? '⭐' : '💰'}
                  </span>
                  {selectedAction.impact}
                </div>
              </div>

              {selectedAction.type === 'risk' && company.single_source_risks.length > 0 && (
                <div>
                  <h3 style={{ marginBottom: '1rem' }}>Single-Source Ingredients:</h3>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Ingredient</th>
                        <th>Supplier Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {company.single_source_risks.slice(0, 10).map((risk, idx) => (
                        <tr key={idx}>
                          <td>{risk.canonical_name}</td>
                          <td><span className="badge badge-warning">1 supplier</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {selectedAction.type === 'consolidation' && batchingOpps.length > 0 && (
                <div>
                  <h3 style={{ marginBottom: '1rem' }}>Batching Opportunities:</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {batchingOpps.slice(0, 5).map((opp, idx) => (
                      <div key={idx} style={{ padding: '1rem', background: 'var(--card-bg)', borderRadius: '8px' }}>
                        <div style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>{opp.ingredient}</div>
                        <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                          {opp.current_supplier} → {opp.recommended_supplier}
                        </div>
                        <div style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
                          <span className="badge badge-success">+{opp.batching_benefit} ingredients</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

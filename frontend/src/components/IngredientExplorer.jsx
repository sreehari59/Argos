import { useState, useEffect } from 'react'

const API_BASE = 'http://localhost:8000/api'

export default function IngredientExplorer() {
  const [topIngredients, setTopIngredients] = useState([])
  const [selectedIngredient, setSelectedIngredient] = useState(null)
  const [ingredientDetails, setIngredientDetails] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [detailsError, setDetailsError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    
    fetch(`${API_BASE}/analytics/ingredients/top?limit=20`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch ingredients')
        return res.json()
      })
      .then(data => {
        setTopIngredients(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to load ingredients:', err)
        setError('Failed to load ingredient data. Please refresh the page.')
        setLoading(false)
      })
  }, [])

  const handleIngredientClick = (ingredient) => {
    setSelectedIngredient(ingredient)
    setIngredientDetails(null)
    setDetailsLoading(true)
    setDetailsError(null)
    
    fetch(`${API_BASE}/analytics/ingredients/${ingredient.SKU}`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch ingredient details')
        return res.json()
      })
      .then(data => {
        setIngredientDetails(data)
        setDetailsLoading(false)
      })
      .catch(err => {
        console.error('Failed to load ingredient details:', err)
        setDetailsError('Failed to load ingredient details. Please try again.')
        setDetailsLoading(false)
      })
  }

  const getFamilyTypeColor = (type) => {
    switch(type) {
      case 'form_variant': return 'var(--success)'
      case 'functional_substitute': return 'var(--warning)'
      case 'exact_match': return 'var(--primary-light)'
      default: return 'var(--text-muted)'
    }
  }

  const getFamilyTypeLabel = (type) => {
    switch(type) {
      case 'form_variant': return 'Form Variant'
      case 'functional_substitute': return 'Functional Substitute'
      case 'exact_match': return 'Exact Match'
      default: return type
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading ingredient intelligence...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
        <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>⚠️</div>
        <h2>Failed to Load Ingredients</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>{error}</p>
        <button 
          className="btn btn-primary" 
          onClick={() => window.location.reload()}
        >
          Refresh Page
        </button>
      </div>
    )
  }

  return (
    <div className="ingredient-explorer">
      <div className="explorer-header">
        <div>
          <h1>Ingredient Intelligence</h1>
          <p className="explorer-subtitle">
            Analyze ingredient usage patterns, supplier networks, and substitution opportunities across the supply chain
          </p>
        </div>
        <div className="explorer-stats">
          <div className="stat-pill">
            <span className="stat-pill-value">{topIngredients.length}</span>
            <span className="stat-pill-label">Top Ingredients</span>
          </div>
        </div>
      </div>

      <div className="explorer-layout">
        {/* Left Panel: Ingredient List */}
        <div className="ingredient-list-panel">
          <div className="panel-header">
            <h2>Most-Used Ingredients</h2>
            <p className="panel-description">Ranked by usage across all products</p>
          </div>
          
          <div className="ingredient-list">
            {topIngredients.map((ingredient, idx) => (
              <div
                key={idx}
                className={`ingredient-list-item ${selectedIngredient?.SKU === ingredient.SKU ? 'active' : ''}`}
                onClick={() => handleIngredientClick(ingredient)}
              >
                <div className="ingredient-rank">#{idx + 1}</div>
                <div className="ingredient-info">
                  <div className="ingredient-name-row">
                    <span className="ingredient-name">{ingredient.canonical_name || ingredient.SKU}</span>
                    {ingredient.family_type && (
                      <span 
                        className="family-type-badge"
                        style={{ borderColor: getFamilyTypeColor(ingredient.family_type) }}
                      >
                        {getFamilyTypeLabel(ingredient.family_type)}
                      </span>
                    )}
                  </div>
                  <div className="ingredient-stats-row">
                    <span className="stat-item">
                      <span className="stat-icon">📦</span>
                      {ingredient.usage_count} products
                    </span>
                    <span className="stat-item">
                      <span className="stat-icon">🏢</span>
                      {ingredient.company_count} companies
                    </span>
                    <span className="stat-item">
                      <span className="stat-icon">🏭</span>
                      {ingredient.supplier_count} suppliers
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Panel: Ingredient Details */}
        <div className="ingredient-details-panel">
          {!selectedIngredient ? (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <h3>Select an ingredient to explore</h3>
              <p>Click any ingredient from the list to see detailed analytics, company usage, suppliers, and substitution patterns</p>
            </div>
          ) : detailsError ? (
            <div className="empty-state">
              <div className="empty-icon">⚠️</div>
              <h3>Error Loading Details</h3>
              <p>{detailsError}</p>
              <button 
                className="btn btn-primary" 
                onClick={() => handleIngredientClick(selectedIngredient)}
                style={{ marginTop: '1rem' }}
              >
                Retry
              </button>
            </div>
          ) : detailsLoading || !ingredientDetails ? (
            <div className="loading-container">
              <div className="loading-spinner"></div>
              <p>Loading ingredient details...</p>
            </div>
          ) : (
            <div className="details-content">
              {/* Ingredient Header */}
              <div className="details-header">
                <div>
                  <h2>{ingredientDetails.canonical_name}</h2>
                  <div className="details-meta">
                    {ingredientDetails.family_name && (
                      <span className="meta-item">
                        Family: <strong>{ingredientDetails.family_name}</strong>
                      </span>
                    )}
                    <span 
                      className="meta-badge"
                      style={{ 
                        borderColor: getFamilyTypeColor(ingredientDetails.family_type),
                        color: getFamilyTypeColor(ingredientDetails.family_type)
                      }}
                    >
                      {getFamilyTypeLabel(ingredientDetails.family_type)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Usage Statistics */}
              <div className="details-stats-grid">
                <div className="detail-stat-card">
                  <div className="detail-stat-icon">🏢</div>
                  <div className="detail-stat-value">{ingredientDetails.company_count}</div>
                  <div className="detail-stat-label">Companies Using</div>
                </div>
                <div className="detail-stat-card">
                  <div className="detail-stat-icon">🏭</div>
                  <div className="detail-stat-value">{ingredientDetails.supplier_count}</div>
                  <div className="detail-stat-label">Suppliers Providing</div>
                </div>
                <div className="detail-stat-card">
                  <div className="detail-stat-icon">🔄</div>
                  <div className="detail-stat-value">{ingredientDetails.alternatives?.length || 0}</div>
                  <div className="detail-stat-label">Alternatives Available</div>
                </div>
              </div>

              {/* Companies Using This Ingredient */}
              {ingredientDetails.companies_using && ingredientDetails.companies_using.length > 0 && (
                <div className="details-section">
                  <h3>Companies Using This Ingredient</h3>
                  <div className="company-usage-grid">
                    {ingredientDetails.companies_using.map((company, idx) => (
                      <div key={idx} className="company-usage-card">
                        <div className="company-usage-name">{company.Name}</div>
                        <div className="company-usage-count">
                          {company.product_count} {company.product_count === 1 ? 'product' : 'products'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Suppliers Providing This Ingredient */}
              {ingredientDetails.suppliers && ingredientDetails.suppliers.length > 0 && (
                <div className="details-section">
                  <h3>Suppliers Providing This Ingredient</h3>
                  <div className="supplier-grid">
                    {ingredientDetails.suppliers.map((supplier, idx) => (
                      <div key={idx} className="supplier-card">
                        <div className="supplier-icon">🏭</div>
                        <div className="supplier-name">{supplier.Name}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Substitution Alternatives */}
              {ingredientDetails.alternatives && ingredientDetails.alternatives.length > 0 && (
                <div className="details-section">
                  <h3>Substitution Alternatives</h3>
                  <p className="section-description">
                    Other ingredients in the same family that can potentially substitute for this ingredient
                  </p>
                  <div className="alternatives-grid">
                    {ingredientDetails.alternatives.map((alt, idx) => (
                      <div key={idx} className="alternative-card">
                        <div className="alternative-header">
                          <div className="alternative-name">{alt.canonical_name}</div>
                          <span 
                            className="alternative-type-badge"
                            style={{ borderColor: getFamilyTypeColor(alt.family_type) }}
                          >
                            {getFamilyTypeLabel(alt.family_type)}
                          </span>
                        </div>
                        <div className="alternative-stats">
                          <div className="alternative-stat">
                            <span className="alt-stat-label">Used by:</span>
                            <span className="alt-stat-value">{alt.company_count} companies</span>
                          </div>
                          <div className="alternative-stat">
                            <span className="alt-stat-label">Availability:</span>
                            <span className="alt-stat-value">{alt.availability_count} sources</span>
                          </div>
                        </div>
                        {alt.companies_using && alt.companies_using.length > 0 && (
                          <div className="alternative-companies">
                            <div className="companies-label">Companies using this alternative:</div>
                            <div className="companies-tags">
                              {alt.companies_using.slice(0, 5).map((company, cidx) => (
                                <span key={cidx} className="company-tag">{company}</span>
                              ))}
                              {alt.companies_using.length > 5 && (
                                <span className="company-tag more">+{alt.companies_using.length - 5} more</span>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Functional Roles */}
              {ingredientDetails.functional_roles && ingredientDetails.functional_roles.length > 0 && (
                <div className="details-section">
                  <h3>Functional Roles</h3>
                  <div className="roles-grid">
                    {ingredientDetails.functional_roles.map((role, idx) => (
                      <div key={idx} className="role-card">
                        <div className="role-name">{role.functional_role}</div>
                        <div className="role-usage">{role.usage_count} uses</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

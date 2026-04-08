import { useState, useEffect } from 'react'

const API_BASE = 'http://localhost:8000/api'

export default function CompanyView({ companyId, onBack }) {
  const [company, setCompany] = useState(null)
  const [recommendations, setRecommendations] = useState([])

  useEffect(() => {
    fetch(`${API_BASE}/companies/${companyId}`)
      .then(res => res.json())
      .then(data => setCompany(data))
      .catch(err => console.error('Failed to load company:', err))

    fetch(`${API_BASE}/recommendations/diversification/${companyId}`)
      .then(res => res.json())
      .then(data => setRecommendations(data.recommendations || []))
      .catch(err => console.error('Failed to load recommendations:', err))
  }, [companyId])

  if (!company) {
    return <div className="card">Loading...</div>
  }

  return (
    <div>
      <button className="btn btn-secondary" onClick={onBack} style={{ marginBottom: '1rem' }}>
        ← Back to Dashboard
      </button>

      <h1 style={{ marginBottom: '2rem' }}>{company.Name}</h1>

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

      <div className="card">
        <h2>📦 Products</h2>
        <table className="table">
          <thead>
            <tr>
              <th>SKU</th>
            </tr>
          </thead>
          <tbody>
            {company.products.map((product, idx) => (
              <tr key={idx}>
                <td>{product.SKU}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

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
          <p style={{ color: 'var(--text-muted)' }}>No diversification opportunities found.</p>
        )}
      </div>

      <div className="card">
        <h2>🏭 Suppliers</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Supplier</th>
              <th>Materials Supplied</th>
            </tr>
          </thead>
          <tbody>
            {company.suppliers.map((supplier, idx) => (
              <tr key={idx}>
                <td>{supplier.Name}</td>
                <td>{supplier.materials_supplied}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

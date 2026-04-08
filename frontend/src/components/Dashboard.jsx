import { useState, useEffect } from 'react'

const API_BASE = 'http://localhost:8000/api'

export default function Dashboard({ onSelectCompany }) {
  const [stats, setStats] = useState(null)
  const [companies, setCompanies] = useState([])
  const [risks, setRisks] = useState(null)
  const [topRecs, setTopRecs] = useState([])

  useEffect(() => {
    fetch(`${API_BASE}/graph/stats`)
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(err => console.error('Failed to load stats:', err))

    fetch(`${API_BASE}/companies`)
      .then(res => res.json())
      .then(data => setCompanies(data))
      .catch(err => console.error('Failed to load companies:', err))

    fetch(`${API_BASE}/risks`)
      .then(res => res.json())
      .then(data => setRisks(data))
      .catch(err => console.error('Failed to load risks:', err))

    fetch(`${API_BASE}/recommendations/top?limit=10`)
      .then(res => res.json())
      .then(data => setTopRecs(data))
      .catch(err => console.error('Failed to load recommendations:', err))
  }, [])

  if (!stats) {
    return <div className="card">Loading dashboard data...</div>
  }

  return (
    <div>
      <h1 style={{ marginBottom: '2rem' }}>Supply Chain Intelligence Dashboard</h1>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{stats.total_nodes}</div>
          <div className="stat-label">Total Nodes</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.total_edges}</div>
          <div className="stat-label">Relationships</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.node_types.company}</div>
          <div className="stat-label">Companies</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.node_types.ingredient}</div>
          <div className="stat-label">Ingredient Families</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.node_types.supplier}</div>
          <div className="stat-label">Suppliers</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{topRecs.length}</div>
          <div className="stat-label">Top Recommendations</div>
        </div>
      </div>

      <div className="card">
        <h2>🎯 Top Substitution Recommendations</h2>
        {topRecs.length > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Product</th>
                <th>Current</th>
                <th>Substitute</th>
                <th>Role</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {topRecs.slice(0, 10).map((rec, idx) => (
                <tr key={idx}>
                  <td>{rec.company_name}</td>
                  <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {rec.product_sku}
                  </td>
                  <td>{rec.current_canonical_name}</td>
                  <td style={{ color: 'var(--success)' }}>{rec.substitute_canonical_name}</td>
                  <td>
                    <span className="badge badge-success">{rec.functional_role}</span>
                  </td>
                  <td style={{ fontWeight: 'bold' }}>{rec.final_score.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📊</div>
            <p>No recommendations available yet.</p>
            <p style={{ fontSize: '0.875rem' }}>Run the recommendation pipeline to generate substitution candidates.</p>
          </div>
        )}
      </div>

      {risks && (
        <div className="card">
          <h2>⚠️ Supply Chain Risks</h2>
          <h3 style={{ fontSize: '1rem', marginTop: '1.5rem', marginBottom: '0.5rem' }}>
            Single-Source Ingredients ({risks.single_source_ingredients.length})
          </h3>
          <table className="table">
            <thead>
              <tr>
                <th>Ingredient</th>
                <th>Companies Using</th>
                <th>Supplier</th>
              </tr>
            </thead>
            <tbody>
              {risks.single_source_ingredients.slice(0, 5).map((item, idx) => (
                <tr key={idx}>
                  <td>{item.canonical_name}</td>
                  <td>
                    <span className="badge badge-warning">{item.companies_using}</span>
                  </td>
                  <td>{item.supplier_names}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3 style={{ fontSize: '1rem', marginTop: '1.5rem', marginBottom: '0.5rem' }}>
            High-Concentration Suppliers ({risks.supplier_concentration.length})
          </h3>
          <table className="table">
            <thead>
              <tr>
                <th>Supplier</th>
                <th>Companies Served</th>
                <th>Materials Supplied</th>
              </tr>
            </thead>
            <tbody>
              {risks.supplier_concentration.slice(0, 5).map((sup, idx) => (
                <tr key={idx}>
                  <td>{sup.Name}</td>
                  <td>
                    <span className="badge badge-danger">{sup.companies_served}</span>
                  </td>
                  <td>{sup.materials_supplied}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card">
        <h2>🏢 Companies</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Company</th>
              <th>Products</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {companies.slice(0, 20).map((company) => (
              <tr key={company.Id}>
                <td>{company.Name}</td>
                <td>{company.product_count}</td>
                <td>
                  <button 
                    className="btn btn-primary"
                    onClick={() => onSelectCompany(company.Id)}
                  >
                    View Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

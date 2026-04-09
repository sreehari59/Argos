import { useState } from 'react'
import './App.css'
import Dashboard from './components/Dashboard'
import CompanyIntelligence from './components/CompanyIntelligence'
import RecommendationsView from './components/RecommendationsView'
import GraphView from './components/GraphView'
import IngredientExplorer from './components/IngredientExplorer'

function App() {
  const [currentView, setCurrentView] = useState('dashboard')
  const [selectedCompanyId, setSelectedCompanyId] = useState(null)

  const renderView = () => {
    if (selectedCompanyId) {
      return <CompanyIntelligence companyId={selectedCompanyId} onBack={() => setSelectedCompanyId(null)} />
    }

    switch (currentView) {
      case 'dashboard':
        return <Dashboard onSelectCompany={setSelectedCompanyId} />
      case 'recommendations':
        return <RecommendationsView />
      case 'ingredients':
        return <IngredientExplorer />
      case 'graph':
        return <GraphView />
      default:
        return <Dashboard onSelectCompany={setSelectedCompanyId} />
    }
  }

  return (
    <div className="app">
      <nav className="navbar">
        <div className="nav-brand">
          <img src="/ArgosDark.svg" alt="Argos" style={{ height: '2rem' }} />
          <div className="subtitle">AI Supply Chain Intelligence</div>
        </div>
        <div className="nav-links">
          <button 
            className={currentView === 'dashboard' ? 'active' : ''}
            onClick={() => { setCurrentView('dashboard'); setSelectedCompanyId(null); }}
          >
            Dashboard
          </button>
          <button 
            className={currentView === 'ingredients' ? 'active' : ''}
            onClick={() => { setCurrentView('ingredients'); setSelectedCompanyId(null); }}
          >
            Ingredients
          </button>
          <button 
            className={currentView === 'recommendations' ? 'active' : ''}
            onClick={() => { setCurrentView('recommendations'); setSelectedCompanyId(null); }}
          >
            Recommendations
          </button>
          <button 
            className={currentView === 'graph' ? 'active' : ''}
            onClick={() => { setCurrentView('graph'); setSelectedCompanyId(null); }}
          >
            Knowledge Graph
          </button>
        </div>
      </nav>
      <main className="main-content">
        {renderView()}
      </main>
    </div>
  )
}

export default App

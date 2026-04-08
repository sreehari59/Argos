# 🚀 Agnes Full-Stack Setup Guide

This folder contains all the essential files needed to run the Agnes AI Supply Chain Intelligence system.

---

## 📦 What's Included

### Backend (`/backend`)
- **Python FastAPI application** with 15 REST endpoints
- **Data processing pipeline** (ingredients, enrichment, roles, graph, recommendations, compliance, quality scoring)
- **Database utilities** and models
- **Requirements**: `requirements.txt`

### Frontend (`/frontend`)
- **React + Vite application** with premium UI
- **4 main views**: Dashboard, Company Intelligence, Ingredient Explorer, Graph View
- **Dependencies**: `package.json`

### Database
- **db_new.sqlite**: Main database with 61 companies, 149 products, 876 raw materials, 40 suppliers

### Configuration
- **.env**: Environment variables (includes OpenRouter API key)
- **enriched_products.json**: Product enrichment data

### Documentation
- **README.md**: Project overview and features
- **ARCHITECTURE.md**: Complete technical architecture
- **PROJECT_SUMMARY.md**: Comprehensive project summary
- **DEPLOYMENT.md**: Production deployment guide
- **DEMO_GUIDE.md**: 5-minute presentation script
- **DOCUMENTATION_INDEX.md**: Documentation index

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- OpenRouter API key (already in .env)

### Step 1: Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment (from parent directory)
cd ..
python3 -m venv venv
source venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Start the API server
uvicorn main:app --reload --port 8000
```

The backend will be available at: **http://localhost:8000**
API documentation at: **http://localhost:8000/docs**

### Step 2: Frontend Setup

Open a new terminal:

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at: **http://localhost:5173**

---

## 🔄 Running the Data Pipeline (Optional)

If you want to regenerate the recommendations from scratch:

```bash
cd backend
source ../venv/bin/activate

# Run pipeline in order
python ingredients.py      # Ingredient resolution
python enrichment.py       # Data enrichment
python roles.py           # Functional role labeling
python graph.py           # Knowledge graph construction
python recommendations.py  # Generate substitution candidates
python llm_compliance.py  # LLM compliance scoring
python quality_scoring.py # Quality & final scoring
```

---

## 📊 System Metrics

- **387 nodes** in knowledge graph
- **1,812 edges** (relationships)
- **7,362 substitution recommendations** generated
- **100% functional role coverage** (1,528 BOM components)
- **18 supply chain risks** identified
- **15 consolidation opportunities** discovered

---

## 🎯 Key Features

1. **Intelligent Ingredient Resolution**: 876 materials → 137 families
2. **Functional Role Labeling**: 18 categories, 100% coverage
3. **3-Factor Recommendation Engine**: Compliance × (Quality + Priority + Family)
4. **Supply Chain Risk Analysis**: Single-source dependencies, concentration risks
5. **Consolidation Optimizer**: Reduce supplier complexity
6. **Company Intelligence Dashboard**: Health scores, priority actions
7. **Ingredient Explorer**: Top ingredients, usage analytics

---

## 📡 API Endpoints

### Core Endpoints
- `GET /api/graph` - Full knowledge graph
- `GET /api/companies` - All companies
- `GET /api/companies/{id}` - Company details
- `GET /api/recommendations/top` - Top recommendations
- `GET /api/risks` - Supply chain risks

### Analytics Endpoints
- `GET /api/analytics/ingredients/top` - Most-used ingredients
- `GET /api/analytics/ingredients/{sku}` - Ingredient details
- `GET /api/analytics/company/{id}/health` - Supply chain health score
- `GET /api/analytics/batching` - Consolidation opportunities

---

## 🛠️ Tech Stack

**Backend**: FastAPI, SQLite, NetworkX, OpenRouter (NVIDIA Nemotron LLM)
**Frontend**: React 18, Vite, Canvas API
**Intelligence**: Hybrid AI (Rule-based + LLM)

---

## 📚 Documentation

- **README.md** - Project overview
- **ARCHITECTURE.md** - Technical deep dive
- **PROJECT_SUMMARY.md** - Complete project summary
- **DEPLOYMENT.md** - Production deployment
- **DEMO_GUIDE.md** - Presentation guide

---

## 🎓 Built For

**Q-Hack × Spherecast Hackathon**
AI Supply Chain Manager for CPG raw material sourcing

---

## 🙏 Credits

Built by Shivam Suchak

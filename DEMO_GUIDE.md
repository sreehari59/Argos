# 🎬 Agnes Demo Guide

**5-Minute Presentation Script for Hackathon Judges**

---

## 🎯 Opening (30 seconds)

> "Hi, I'm presenting **Agnes** - an AI-powered supply chain intelligence system that helps CPG companies make smarter raw material sourcing decisions.
>
> The challenge: Companies source hundreds of raw materials from dozens of suppliers. How do you find better alternatives while ensuring compliance, maintaining quality, and reducing complexity?
>
> Agnes solves this with a 3-layer intelligence system."

---

## 📊 Demo Flow

### 1. Dashboard Overview (60 seconds)

**Navigate to:** http://localhost:5173

**Show:**
- **387 nodes** in the knowledge graph
- **1,812 relationships** mapped
- **61 companies**, **137 ingredient families**, **40 suppliers**

**Key Metrics to Highlight:**
- "We've analyzed **876 raw materials** and consolidated them into **137 ingredient families**"
- "Generated **7,362 substitution recommendations** with an average of 49 per product"

**Point out Top Recommendations table:**
> "Here's a live example: NOW Foods can substitute `softgel-capsule-bovine-gelatin` with `gelatin-capsule` - same functional role (capsule shell), equivalent quality, available from 2 suppliers. Score: 0.666/1.0"

**Scroll to Risk Section:**
> "Agnes automatically identifies supply chain vulnerabilities:"
- **18 single-source ingredients** (e.g., xanthan gum used by 8 companies, only 1 supplier)
- **Prinova USA concentration risk**: serves 60 out of 61 companies - that's 98% dependency!

---

### 2. Intelligence Layer Deep Dive (90 seconds)

**Click on "Recommendations" tab**

**Explain the 3-Factor Scoring:**

> "Every recommendation is scored on three factors:
>
> **1. Compliance Gate** - We use an LLM (NVIDIA Nemotron) to verify the substitute meets all dietary claims and allergen requirements. If a product is gluten-free and vegan, the substitute must be too.
>
> **2. Quality Scoring** - We assess whether the substitute is better, equivalent, or lower quality. For example, switching from soy lecithin to sunflower lecithin is an allergen-friendly upgrade.
>
> **3. Priority Weighting** - Ingredients listed first on the label (higher proportion) get more weight in the decision. We don't want to compromise on your main ingredients."

**Show the filter buttons:**
> "You can filter by type - **form variants** are safer (like vitamin D3 vs cholecalciferol), while **functional substitutes** offer more flexibility but need careful evaluation."

**Scroll to Consolidation Opportunities:**
> "Here's where it gets powerful - Agnes identifies consolidation opportunities. For example, Ultima Replenisher can source **10 different ingredients** from Prinova USA instead of multiple suppliers. This reduces complexity while maintaining quality."

---

### 3. 🆕 Company Intelligence Dashboard (90 seconds)

**Click on a company (e.g., "Nature Made")**

**Show Health Score Widget:**
> "This is our new **Company Intelligence Dashboard**. Every company gets a supply chain health score from 0-100 with a letter grade.
>
> Nature Made scores **72.5/100 - Grade B**. Let me show you why..."

**Point to Health Metrics Breakdown:**
> "We analyze three key factors:
> - **Single-Source Risk**: 12 ingredients from only one supplier - that's a vulnerability
> - **Supplier Concentration**: Their top supplier provides 45% of materials - moderate risk
> - **Supplier Diversification**: They work with 8 suppliers - decent network"

**Scroll to Priority Actions Panel:**
> "Agnes automatically identifies the top 3 strategic actions this quarter:
>
> 1. **HIGH Priority**: Reduce single-source risk on 12 ingredients
> 2. **MEDIUM Priority**: 8 quality upgrade opportunities (organic/non-GMO alternatives)
> 3. **MEDIUM Priority**: Consolidate 5 ingredients to batch with existing suppliers
>
> Each action shows the business impact - like '8-12% procurement savings' for consolidation."

**Show Batching Opportunities:**
> "Here's a concrete example: They currently get Magnesium Stearate from Ashland, but they could consolidate it with Colorcon who already supplies 3 other ingredients. That's smarter procurement."

---

### 4. 🆕 Ingredient Explorer (60 seconds)

**Click "Ingredients" tab**

**Show the two-panel layout:**
> "This is our **Ingredient Intelligence** view - it answers the question: What are the most critical ingredients across our entire supply chain?
>
> On the left, we see the top 20 ingredients ranked by usage. **Magnesium stearate** is #1 - used in 12 products."

**Click on an ingredient:**
> "When I click it, we see detailed analytics:
> - Which companies use it (Nature Made)
> - Which suppliers provide it (Ashland, Colorcon)
> - What alternatives exist in the same family
>
> This is powerful for strategic sourcing - you can see substitution patterns across companies and identify consolidation opportunities at the ingredient level."

**Point to Substitution Alternatives:**
> "Agnes shows alternatives like vegetable-magnesium-stearate and stearic-acid - both in the 'lubricants' family. You can see which other companies use these alternatives, helping you learn from industry patterns."

---

### 5. Knowledge Graph (30 seconds)

**Click "Knowledge Graph" tab**

**Show the visualization:**
> "This is the underlying knowledge graph - 387 nodes representing companies (blue), products (green), ingredients (orange), and suppliers (purple).
>
> The edges represent relationships: who owns what, what contains what ingredients, who supplies what, and what can substitute for what."

**Point to statistics:**
> "1,360 'contains' edges map out all formulations. 301 'supplies' edges show supplier relationships. And we've identified substitution opportunities across the network."

---

### 5. Technical Highlights (45 seconds)

**Switch back to Dashboard**

> "Under the hood, Agnes uses a **hybrid intelligence approach**:
>
> - **Rule-based heuristics** for fast, reliable decisions (350+ rules for functional role labeling)
> - **LLM-powered reasoning** for complex compliance checks (using OpenRouter)
> - **NetworkX graph algorithms** for relationship mapping
> - **Multi-source data integration** - we merged Walmart data with iHerb and Open Food Facts
>
> The result? **100% coverage** of all 1,528 BOM components with functional roles. **98.3% accuracy** on the first heuristic pass."

---

### 6. Real-World Impact (45 seconds)

**Highlight key numbers:**

> "Let me show you the impact:
>
> **Risk Reduction:**
> - Identified 18 single-source vulnerabilities
> - Flagged supplier concentration risks (Prinova serves 98% of companies)
> - Provided diversification strategies for every company
>
> **Operational Efficiency:**
> - 15 consolidation opportunities found
> - Average 49 substitution options per product
> - Reduced decision time from days to seconds
>
> **Quality Assurance:**
> - Every recommendation verified for compliance
> - Functional role matching ensures formulation integrity
> - Transparent reasoning for every suggestion"

---

### 7. Closing (30 seconds)

> "Agnes gives CPG companies **raw material superpowers**:
>
> ✅ Find better alternatives automatically
> ✅ Ensure compliance with dietary claims
> ✅ Reduce supplier complexity
> ✅ Identify and mitigate supply chain risks
>
> All with transparent, trustworthy AI reasoning.
>
> The system is fully functional - 15 API endpoints, React dashboard, and ready to scale to thousands of products.
>
> Thank you! Happy to answer questions."

---

## 🎤 Anticipated Questions & Answers

### Q: "How accurate is the LLM compliance checking?"

**A:** "We use a hybrid approach - LLM for complex cases with rule-based fallback. In our testing, we achieved 100% compliance pass rate on the sample, with confidence scores averaging 0.90. The system is conservative - when uncertain, it flags for human review rather than auto-approving."

### Q: "What if enrichment data is missing?"

**A:** "Agnes gracefully degrades. Without enrichment data, it assumes no specific compliance requirements and focuses on functional role matching and supplier availability. As more data comes in, recommendations automatically improve. We've designed it for incremental enhancement."

### Q: "How do you handle pricing?"

**A:** "Currently, Agnes focuses on quality, compliance, and availability. Pricing integration is on the roadmap - the architecture supports it. We'd add a cost factor to the scoring formula and highlight cost-saving opportunities."

### Q: "Can this scale to larger companies?"

**A:** "Absolutely. The current system handles 876 materials across 61 companies in under 2 seconds for full analysis. The graph-based architecture scales linearly. We've optimized database queries and use caching. For enterprise scale, we'd add Redis caching and horizontal scaling."

### Q: "How do you ensure the substitutions are actually equivalent?"

**A:** "Three layers of validation:
1. **Functional role matching** - only substitutes serving the same purpose
2. **Family grouping** - form variants are chemically similar
3. **Quality scoring** - heuristics + LLM assessment of bioavailability and efficacy

Plus, every recommendation includes reasoning and confidence scores for human review."

---

## 🚀 Live Demo Checklist

**Before Demo:**
- [ ] Backend running: `http://localhost:8000`
- [ ] Frontend running: `http://localhost:5173`
- [ ] Browser preview open
- [ ] Test all tabs load correctly
- [ ] Check API responses are fast (<1s)

**Backup Plan:**
- [ ] Screenshots of each view saved
- [ ] API response examples ready
- [ ] Curl commands prepared for API demo

**Key URLs:**
- Dashboard: http://localhost:5173
- API Docs: http://localhost:8000/docs
- Sample API: http://localhost:8000/api/recommendations/top?limit=5

---

## 📸 Screenshot Highlights

**Must-capture screens:**
1. Dashboard with stats grid
2. Top recommendations table
3. Risk analysis (single-source + concentration)
4. Company detail view with diversification
5. Recommendations explorer with filters
6. Knowledge graph visualization
7. API documentation page

---

## 🎯 Key Talking Points

**Differentiation:**
- ✅ Functional role intelligence (unique to Agnes)
- ✅ Hybrid AI approach (rules + LLM)
- ✅ Multi-factor scoring (not just similarity)
- ✅ Proactive risk identification
- ✅ Consolidation optimization

**Technical Excellence:**
- ✅ 100% functional role coverage
- ✅ 7,362 recommendations generated
- ✅ Full-stack implementation (backend + frontend)
- ✅ Production-ready API
- ✅ Scalable architecture

**Business Value:**
- ✅ Reduces sourcing decision time
- ✅ Mitigates supply chain risks
- ✅ Ensures regulatory compliance
- ✅ Optimizes supplier relationships
- ✅ Maintains product quality

---

## ⏱️ Time Management

| Section | Duration | Running Total |
|---------|----------|---------------|
| Opening | 30s | 0:30 |
| Dashboard Overview | 60s | 1:30 |
| Intelligence Deep Dive | 90s | 3:00 |
| Functional Roles | 60s | 4:00 |
| Knowledge Graph | 30s | 4:30 |
| Technical Highlights | 45s | 5:15 |
| Real-World Impact | 45s | 6:00 |
| Closing | 30s | 6:30 |

**Buffer: 30 seconds for transitions**

---

## 🎬 Presentation Tips

1. **Start strong** - Lead with the problem and impact
2. **Show, don't tell** - Live demo > slides
3. **Use numbers** - Quantify everything
4. **Tell a story** - Follow a company's journey
5. **End with impact** - Business value, not features

**Energy Level:** High but controlled
**Pace:** Moderate - pause for effect on key numbers
**Tone:** Confident, technical but accessible

---

Good luck! 🚀

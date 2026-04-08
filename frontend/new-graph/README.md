# Supply Chain Knowledge Graph

This folder contains everything you need to run the interactive supply chain knowledge graph visualization.

## 📁 Files Included

1. **knowledge-graph.html** - Interactive visualization (main file)
2. **comprehensive_supply_chain.json** - Supply chain data (184 KB)
3. **db_filtered.sqlite** - Filtered SQLite database with validated supply chains
4. **comprehensive_sqlite_analysis.py** - Python script to regenerate data from database
5. **start.sh** - Quick start script to launch the server
6. **README.md** - This file

## 🚀 Quick Start

### Option 1: Using the start script (Recommended)
```bash
cd new-graph
./start.sh
```

### Option 2: Manual start
```bash
cd new-graph
python3 -m http.server 8765
```

Then open your browser and go to:
**http://localhost:8765/knowledge-graph.html**

## 📊 What's in the Graph

- **61 companies** with validated supply chains
- **149 finished goods** (all with raw materials)
- **876 raw materials** (all with suppliers)
- **40 suppliers**
- **33 products** with pricing data ($2.28 - $45.00)

## 🎯 Features

### Four Views
1. **Full Chain** - Complete supply chain: Company → FG → RM → Supplier
2. **Materials** - Bill of Materials view (top 50 hub materials)
3. **Risk** - Single-source risk analysis
4. **Products** - Product similarity and intelligence

### Interactive Features
- **Click nodes** to see detailed information
- **Search** for companies, products, suppliers, or materials
- **Filters** (Full Chain view only):
  - Company filter - Select specific companies
  - Supplier filter - Select specific suppliers
  - Category filters - Filter by product category
  - Certification filters - Filter by dietary certifications
- **Zoom & Pan** - Navigate the graph
- **Hover** - See quick info on any node

### Company & Supplier Filters (Full Chain View)
- Select one or more companies to see only their supply chains
- Select one or more suppliers to see which products they supply
- Hold Cmd (Mac) or Ctrl (Windows) to select multiple items
- Filters work together for precise exploration

## 🔄 Regenerating Data

If you update the database (`db_filtered.sqlite`), regenerate the JSON:

```bash
python3 comprehensive_sqlite_analysis.py
```

This will create a new `comprehensive_supply_chain.json` file.

Then refresh your browser (Cmd+Shift+R or Ctrl+Shift+R) to see the updated data.

## 📋 Data Requirements

The knowledge graph expects:
- All companies must have finished goods
- All finished goods must have raw materials in their BOM
- All raw materials must have at least one supplier

The `db_filtered.sqlite` database already meets these requirements.

## 🛠️ Technical Details

- **Visualization**: D3.js force-directed graph
- **Data Format**: JSON
- **Database**: SQLite
- **Server**: Python HTTP server (any static file server works)
- **Browser**: Modern browser with JavaScript enabled

## 🎨 Node Colors

- 🔵 **Blue** - Companies
- 🟢 **Green** - Finished Goods
- 🔴 **Red** - Raw Materials (darker = single-source risk)
- 🟡 **Yellow** - Suppliers

## 💡 Tips

1. **Start with Full Chain view** to see the complete supply chain
2. **Use company filter** to focus on specific brands (e.g., "New Chapter", "Optimum Nutrition")
3. **Use supplier filter** to see supplier reach (e.g., "Prinova USA" supplies to 60 companies)
4. **Click nodes** to explore connections and see pricing data
5. **Switch views** to analyze different aspects (materials, risk, products)

## 📞 Support

For questions or issues, refer to the main project documentation.

---

**Last Updated**: April 8, 2026
**Data Source**: Filtered SQLite Database (db_filtered.sqlite) - Validated Supply Chains Only

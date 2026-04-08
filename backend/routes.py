"""
FastAPI route handlers for Agnes Network Intelligence API.
"""
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException

from db import query
from graph import get_graph, get_graph_json
from ingredients import parse_ingredient_name

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

@router.get("/graph")
def get_full_graph():
    """Full graph data (nodes + edges) for frontend visualization."""
    return get_graph_json()


@router.get("/graph/stats")
def get_graph_stats():
    """Summary statistics of the knowledge graph."""
    G = get_graph()
    node_types = {}
    for _, data in G.nodes(data=True):
        t = data.get('type', 'unknown')
        node_types[t] = node_types.get(t, 0) + 1

    edge_types = {}
    for _, _, data in G.edges(data=True):
        t = data.get('type', 'unknown')
        edge_types[t] = edge_types.get(t, 0) + 1

    return {
        'total_nodes': G.number_of_nodes(),
        'total_edges': G.number_of_edges(),
        'node_types': node_types,
        'edge_types': edge_types,
    }


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------

@router.get("/companies")
def list_companies():
    """All companies with product counts."""
    rows = query("""
        SELECT c.Id, c.Name,
               COUNT(DISTINCT p.Id) as product_count
        FROM Company c
        LEFT JOIN Product p ON c.Id = p.CompanyId AND p.Type = 'finished-good'
        GROUP BY c.Id
        ORDER BY c.Name
    """)
    return rows


@router.get("/companies/{company_id}")
def get_company(company_id: int):
    """Company detail with products, ingredients, suppliers, and risks."""
    company = query("SELECT Id, Name FROM Company WHERE Id = ?", (company_id,))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company = company[0]

    # Products
    products = query("""
        SELECT p.Id, p.SKU
        FROM Product p
        WHERE p.CompanyId = ? AND p.Type = 'finished-good'
    """, (company_id,))

    # Ingredients used (with roles) - handle missing Ingredient_Role table
    try:
        ingredients = query("""
            SELECT DISTINCT ir.canonical_name, ir.functional_role,
                   ifam.family_name, ifam.family_type
            FROM Ingredient_Role ir
            JOIN BOM b ON ir.product_id = b.ProducedProductId
            JOIN Product p ON b.ProducedProductId = p.Id
            LEFT JOIN Ingredient_Family ifam ON ir.canonical_name = ifam.canonical_name
            WHERE p.CompanyId = ?
            ORDER BY ir.functional_role, ir.canonical_name
        """, (company_id,))
    except:
        # Fallback: get ingredients without roles
        ingredients = query("""
            SELECT DISTINCT ifam.canonical_name, ifam.family_name, ifam.family_type
            FROM Ingredient_Family ifam
            JOIN Ingredient_Family_Member ifm ON ifam.Id = ifm.family_id
            JOIN Product p_rm ON ifm.product_id = p_rm.Id
            JOIN BOM_Component bc ON p_rm.Id = bc.ConsumedProductId
            JOIN BOM b ON bc.BOMId = b.Id
            JOIN Product p_fg ON b.ProducedProductId = p_fg.Id
            WHERE p_fg.CompanyId = ?
            ORDER BY ifam.canonical_name
        """, (company_id,))

    # Suppliers
    suppliers = query("""
        SELECT DISTINCT s.Id, s.Name, COUNT(DISTINCT sp.ProductId) as materials_supplied
        FROM Supplier s
        JOIN Supplier_Product sp ON s.Id = sp.SupplierId
        JOIN Product p_rm ON sp.ProductId = p_rm.Id
        JOIN BOM_Component bc ON p_rm.Id = bc.ConsumedProductId
        JOIN BOM b ON bc.BOMId = b.Id
        JOIN Product p_fg ON b.ProducedProductId = p_fg.Id
        WHERE p_fg.CompanyId = ?
        GROUP BY s.Id
        ORDER BY materials_supplied DESC
    """, (company_id,))

    # Single-source ingredients for this company
    try:
        single_source = query("""
            SELECT ir.canonical_name, ir.functional_role, COUNT(DISTINCT sp.SupplierId) as supplier_count
            FROM Ingredient_Role ir
            JOIN BOM b ON ir.product_id = b.ProducedProductId
            JOIN Product p_fg ON b.ProducedProductId = p_fg.Id
            JOIN Supplier_Product sp ON ir.ingredient_id = sp.ProductId
            WHERE p_fg.CompanyId = ?
            GROUP BY ir.canonical_name
            HAVING supplier_count = 1
            ORDER BY ir.canonical_name
        """, (company_id,))
    except:
        # Fallback: get single-source ingredients without roles
        single_source = query("""
            SELECT ifam.canonical_name, COUNT(DISTINCT sp.SupplierId) as supplier_count
            FROM Ingredient_Family ifam
            JOIN Ingredient_Family_Member ifm ON ifam.Id = ifm.family_id
            JOIN Product p_rm ON ifm.product_id = p_rm.Id
            JOIN BOM_Component bc ON p_rm.Id = bc.ConsumedProductId
            JOIN BOM b ON bc.BOMId = b.Id
            JOIN Product p_fg ON b.ProducedProductId = p_fg.Id
            JOIN Supplier_Product sp ON p_rm.Id = sp.ProductId
            WHERE p_fg.CompanyId = ?
            GROUP BY ifam.canonical_name
            HAVING supplier_count = 1
            ORDER BY ifam.canonical_name
        """, (company_id,))

    # Enrichment data for this company's products
    try:
        enrichment = query("""
            SELECT ce.*
            FROM Clean_Enrichment ce
            JOIN Product p ON ce.product_id = p.Id
            WHERE p.CompanyId = ?
        """, (company_id,))
    except:
        enrichment = []

    return {
        **company,
        'products': products,
        'ingredients': ingredients,
        'suppliers': suppliers,
        'single_source_risks': single_source,
        'enrichment': enrichment,
    }


# ---------------------------------------------------------------------------
# Ingredients
# ---------------------------------------------------------------------------

@router.get("/ingredients")
def list_ingredients():
    """All canonical ingredients with family info and role distribution."""
    rows = query("""
        SELECT ifam.family_name,
               ifam.family_type,
               GROUP_CONCAT(DISTINCT ifam.canonical_name) as canonical_names,
               COUNT(DISTINCT ifm.product_id) as used_by_materials
        FROM Ingredient_Family ifam
        LEFT JOIN Ingredient_Family_Member ifm ON ifam.Id = ifm.family_id
        GROUP BY ifam.family_name, ifam.family_type
        ORDER BY used_by_materials DESC
    """)
    return rows


@router.get("/ingredients/{family_name}/substitutes")
def get_ingredient_substitutes(family_name: str):
    """Substitution candidates for an ingredient family."""
    # Get the family info
    family = query(
        "SELECT DISTINCT family_name, family_type FROM Ingredient_Family WHERE family_name = ?",
        (family_name,)
    )
    if not family:
        raise HTTPException(status_code=404, detail="Ingredient family not found")

    family_type = family[0]['family_type']

    # Get all canonical names in this family
    members = query(
        "SELECT DISTINCT canonical_name FROM Ingredient_Family WHERE family_name = ?",
        (family_name,)
    )
    member_names = [m['canonical_name'] for m in members]

    # Get which companies use each variant
    usage = query("""
        SELECT ifam.canonical_name, c.Name as company_name, p.SKU as product_sku
        FROM Ingredient_Family ifam
        JOIN Ingredient_Family_Member ifm ON ifam.Id = ifm.family_id
        JOIN Product p_rm ON ifm.product_id = p_rm.Id
        JOIN BOM_Component bc ON p_rm.Id = bc.ConsumedProductId
        JOIN BOM b ON bc.BOMId = b.Id
        JOIN Product p ON b.ProducedProductId = p.Id
        JOIN Company c ON p.CompanyId = c.Id
        WHERE ifam.family_name = ?
        ORDER BY ifam.canonical_name, c.Name
    """, (family_name,))

    # Get suppliers for each variant
    supply = query("""
        SELECT DISTINCT ifam.canonical_name, s.Name as supplier_name
        FROM Ingredient_Family ifam
        JOIN Ingredient_Family_Member ifm ON ifam.Id = ifm.family_id
        JOIN Supplier_Product sp ON ifm.product_id = sp.ProductId
        JOIN Supplier s ON sp.SupplierId = s.Id
        WHERE ifam.family_name = ?
    """, (family_name,))

    # Get functional roles
    roles = query("""
        SELECT DISTINCT ir.canonical_name, ir.functional_role
        FROM Ingredient_Role ir
        WHERE ir.canonical_name IN ({})
    """.format(','.join('?' * len(member_names))), tuple(member_names))

    # Check graph for cross-family substitution edges
    G = get_graph()
    node_id = f"ingredient:{family_name}"
    cross_subs = []
    if G.has_node(node_id):
        for _, target, edge_data in G.edges(node_id, data=True):
            if edge_data.get('type') == 'substitutes':
                cross_subs.append({
                    'target': target.replace('ingredient:', ''),
                    'family_type': edge_data.get('family_type'),
                    'weight': edge_data.get('weight'),
                })

    return {
        'family_name': family_name,
        'family_type': family_type,
        'member_names': member_names,
        'usage': usage,
        'suppliers': supply,
        'functional_roles': roles,
        'cross_family_substitutes': cross_subs,
    }


@router.get("/ingredients/{family_name}/role")
def get_ingredient_role(family_name: str, product_id: Optional[int] = None):
    """Functional role of an ingredient, optionally in a specific product."""
    if product_id:
        roles = query("""
            SELECT ir.product_id, ir.canonical_name, ir.functional_role,
                   ir.confidence, ir.method
            FROM Ingredient_Role ir
            JOIN Ingredient_Family ifam ON ir.canonical_name = ifam.canonical_name
            WHERE ifam.family_name = ? AND ir.product_id = ?
        """, (family_name, product_id))
    else:
        roles = query("""
            SELECT DISTINCT ir.functional_role, COUNT(*) as count
            FROM Ingredient_Role ir
            JOIN Ingredient_Family ifam ON ir.canonical_name = ifam.canonical_name
            WHERE ifam.family_name = ?
            GROUP BY ir.functional_role
            ORDER BY count DESC
        """, (family_name,))

    if not roles:
        raise HTTPException(status_code=404, detail="No role data found")

    return roles


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@router.get("/products/{product_id}/formulation")
def get_product_formulation(product_id: int):
    """Full formulation breakdown: each ingredient with role and priority."""
    product = query("SELECT Id, SKU, CompanyId FROM Product WHERE Id = ?", (product_id,))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product = product[0]

    company = query("SELECT Name FROM Company WHERE Id = ?", (product['CompanyId'],))
    company_name = company[0]['Name'] if company else 'Unknown'

    # Get all ingredients with roles
    ingredients = query("""
        SELECT ir.ingredient_id, ir.canonical_name, ir.functional_role,
               ir.confidence, ir.method,
               ifam.family_name, ifam.family_type
        FROM Ingredient_Role ir
        LEFT JOIN Ingredient_Family ifam ON ir.canonical_name = ifam.canonical_name
        WHERE ir.product_id = ?
        ORDER BY ir.functional_role, ir.canonical_name
    """, (product_id,))

    # Get enrichment data
    enrichment = query(
        "SELECT * FROM Clean_Enrichment WHERE product_id = ?",
        (product_id,)
    )

    # Get suppliers for each ingredient
    for ing in ingredients:
        suppliers = query("""
            SELECT DISTINCT s.Name
            FROM Supplier_Product sp
            JOIN Supplier s ON sp.SupplierId = s.Id
            WHERE sp.ProductId = ?
        """, (ing['ingredient_id'],))
        ing['suppliers'] = [s['Name'] for s in suppliers]

    # Group by role for the response
    by_role = {}
    for ing in ingredients:
        role = ing['functional_role']
        if role not in by_role:
            by_role[role] = []
        by_role[role].append(ing)

    return {
        'product_id': product_id,
        'sku': product['SKU'],
        'company_name': company_name,
        'total_ingredients': len(ingredients),
        'ingredients': ingredients,
        'by_role': by_role,
        'enrichment': enrichment[0] if enrichment else None,
    }


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------

@router.get("/suppliers")
def list_suppliers():
    """All suppliers with coverage stats."""
    rows = query("""
        SELECT s.Id, s.Name,
               COUNT(DISTINCT sp.ProductId) as materials_supplied,
               COUNT(DISTINCT p.CompanyId) as companies_served
        FROM Supplier s
        LEFT JOIN Supplier_Product sp ON s.Id = sp.SupplierId
        LEFT JOIN Product p ON sp.ProductId = p.Id
        GROUP BY s.Id
        ORDER BY materials_supplied DESC
    """)
    return rows


@router.get("/suppliers/{supplier_id}")
def get_supplier(supplier_id: int):
    """Supplier detail with materials, companies served, and competitors."""
    supplier = query("SELECT Id, Name FROM Supplier WHERE Id = ?", (supplier_id,))
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    supplier = supplier[0]

    # Materials supplied
    materials = query("""
        SELECT DISTINCT p.Id, p.SKU,
               ifam.family_name, ifam.family_type
        FROM Supplier_Product sp
        JOIN Product p ON sp.ProductId = p.Id
        LEFT JOIN Ingredient_Family_Member ifm ON p.Id = ifm.product_id
        LEFT JOIN Ingredient_Family ifam ON ifm.family_id = ifam.Id
        WHERE sp.SupplierId = ?
        ORDER BY ifam.family_name
    """, (supplier_id,))

    # Companies served
    companies = query("""
        SELECT DISTINCT c.Id, c.Name, COUNT(DISTINCT sp.ProductId) as materials_count
        FROM Supplier_Product sp
        JOIN Product p ON sp.ProductId = p.Id
        JOIN Company c ON p.CompanyId = c.Id
        WHERE sp.SupplierId = ?
        GROUP BY c.Id
        ORDER BY materials_count DESC
    """, (supplier_id,))

    # Competing suppliers (share ingredients)
    competitors = query("""
        SELECT s2.Id, s2.Name, COUNT(DISTINCT ifam.family_name) as shared_ingredients
        FROM Supplier_Product sp1
        JOIN Product p1 ON sp1.ProductId = p1.Id
        JOIN Ingredient_Family_Member ifm1 ON p1.Id = ifm1.product_id
        JOIN Ingredient_Family ifam ON ifm1.family_id = ifam.Id
        JOIN Ingredient_Family_Member ifm2 ON ifam.Id = ifm2.family_id
        JOIN Supplier_Product sp2 ON ifm2.product_id = sp2.ProductId
        JOIN Supplier s2 ON sp2.SupplierId = s2.Id
        WHERE sp1.SupplierId = ? AND sp2.SupplierId != ?
        GROUP BY s2.Id
        ORDER BY shared_ingredients DESC
        LIMIT 10
    """, (supplier_id, supplier_id))

    return {
        **supplier,
        'materials': materials,
        'companies_served': companies,
        'competitors': competitors,
    }


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------

@router.get("/enrichment/{product_id}")
def get_enrichment(product_id: int):
    """Clean enrichment data for a product."""
    rows = query("SELECT * FROM Clean_Enrichment WHERE product_id = ?", (product_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="No enrichment data for this product")
    return rows[0]


# ---------------------------------------------------------------------------
# Risks
# ---------------------------------------------------------------------------

@router.get("/risks")
def get_risks():
    """Single-source risks and concentration risks."""
    # Single-source ingredients (only 1 supplier but used by multiple companies)
    try:
        single_source = query("""
            SELECT ir.canonical_name,
                   COUNT(DISTINCT p_fg.CompanyId) as companies_using,
                   COUNT(DISTINCT sp.SupplierId) as num_suppliers,
                   GROUP_CONCAT(DISTINCT s.Name) as supplier_names
            FROM Ingredient_Role ir
            JOIN BOM b ON ir.product_id = b.ProducedProductId
            JOIN Product p_fg ON b.ProducedProductId = p_fg.Id
            JOIN Supplier_Product sp ON ir.ingredient_id = sp.ProductId
            JOIN Supplier s ON sp.SupplierId = s.Id
            GROUP BY ir.canonical_name
            HAVING num_suppliers = 1 AND companies_using > 1
            ORDER BY companies_using DESC
        """)
    except:
        # Fallback without Ingredient_Role
        single_source = query("""
            SELECT ifam.canonical_name,
                   COUNT(DISTINCT p_fg.CompanyId) as companies_using,
                   COUNT(DISTINCT sp.SupplierId) as num_suppliers,
                   GROUP_CONCAT(DISTINCT s.Name) as supplier_names
            FROM Ingredient_Family ifam
            JOIN Ingredient_Family_Member ifm ON ifam.Id = ifm.family_id
            JOIN Product p_rm ON ifm.product_id = p_rm.Id
            JOIN BOM_Component bc ON p_rm.Id = bc.ConsumedProductId
            JOIN BOM b ON bc.BOMId = b.Id
            JOIN Product p_fg ON b.ProducedProductId = p_fg.Id
            JOIN Supplier_Product sp ON p_rm.Id = sp.ProductId
            JOIN Supplier s ON sp.SupplierId = s.Id
            GROUP BY ifam.canonical_name
            HAVING num_suppliers = 1 AND companies_using > 1
            ORDER BY companies_using DESC
        """)

    # Supplier concentration (suppliers serving many companies)
    supplier_concentration = query("""
        SELECT s.Id, s.Name,
               COUNT(DISTINCT p.CompanyId) as companies_served,
               COUNT(DISTINCT sp.ProductId) as materials_supplied
        FROM Supplier s
        JOIN Supplier_Product sp ON s.Id = sp.SupplierId
        JOIN Product p ON sp.ProductId = p.Id
        GROUP BY s.Id
        HAVING companies_served > 10
        ORDER BY companies_served DESC
    """)

    # Companies with high supplier dependency (>80% from one supplier)
    company_dependency = query("""
        SELECT c.Id, c.Name, s.Name as primary_supplier,
               COUNT(DISTINCT sp.ProductId) as from_primary,
               total.total_materials,
               ROUND(COUNT(DISTINCT sp.ProductId) * 100.0 / total.total_materials, 1) as dependency_pct
        FROM Company c
        JOIN Product p ON c.Id = p.CompanyId AND p.Type = 'raw-material'
        JOIN Supplier_Product sp ON p.Id = sp.ProductId
        JOIN Supplier s ON sp.SupplierId = s.Id
        JOIN (
            SELECT p2.CompanyId, COUNT(DISTINCT p2.Id) as total_materials
            FROM Product p2
            WHERE p2.Type = 'raw-material'
            GROUP BY p2.CompanyId
        ) total ON c.Id = total.CompanyId
        GROUP BY c.Id, s.Id
        HAVING dependency_pct > 60
        ORDER BY dependency_pct DESC
    """)

    return {
        'single_source_ingredients': single_source,
        'supplier_concentration': supplier_concentration,
        'company_supplier_dependency': company_dependency,
    }


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

@router.get("/recommendations/product/{product_id}")
def get_product_recommendations(product_id: int, min_score: float = 0.6):
    """Get all substitution recommendations for a product."""
    from recommendations import get_recommendations_for_product
    
    recs = get_recommendations_for_product(product_id)
    
    # Filter by min score
    filtered = [r for r in recs if (r.get('final_score') or 0) >= min_score]
    
    # Group by functional role
    by_role = {}
    for r in filtered:
        role = r['functional_role']
        if role not in by_role:
            by_role[role] = []
        by_role[role].append(r)
    
    return {
        'product_id': product_id,
        'total_recommendations': len(filtered),
        'by_role': by_role,
        'all_recommendations': filtered,
    }


@router.get("/recommendations/top")
def get_top_recommendations(limit: int = 50):
    """Get top recommendations across all products."""
    from recommendations import get_top_recommendations
    
    return get_top_recommendations(limit)


@router.get("/recommendations/consolidation")
def get_consolidation_opportunities(company_id: Optional[int] = None):
    """Get supplier consolidation opportunities."""
    from consolidation import find_consolidation_opportunities
    
    return find_consolidation_opportunities(company_id)


# ---------------------------------------------------------------------------
# Ingredient Analytics
# ---------------------------------------------------------------------------

@router.get("/analytics/ingredients/top")
def get_top_ingredients_analytics(limit: int = 50):
    """Get most frequently used ingredients with usage statistics."""
    from ingredient_analytics import get_top_ingredients
    
    return get_top_ingredients(limit)


@router.get("/analytics/ingredients/{ingredient_sku}")
def get_ingredient_analytics(ingredient_sku: str):
    """Get detailed analytics for a specific ingredient."""
    from ingredient_analytics import get_ingredient_details
    
    details = get_ingredient_details(ingredient_sku)
    if not details:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    return details


@router.get("/analytics/batching")
def get_batching_opportunities_analytics(company_id: Optional[int] = None):
    """Get supplier batching and consolidation opportunities."""
    from ingredient_analytics import get_batching_opportunities
    
    return get_batching_opportunities(company_id)


@router.get("/analytics/company/{company_id}/health")
def get_company_health_score(company_id: int):
    """Get supply chain health score for a company."""
    from ingredient_analytics import get_company_supply_chain_health
    
    return get_company_supply_chain_health(company_id)


@router.get("/recommendations/diversification/{company_id}")
def get_diversification_recommendations(company_id: int):
    """Get supplier diversification recommendations for a company."""
    from consolidation import recommend_diversification
    
    return recommend_diversification(company_id)


@router.get("/recommendations/concentration")
def get_concentration_analysis(min_companies: int = 5):
    """Analyze supplier concentration risks."""
    from consolidation import analyze_supplier_concentration
    
    return analyze_supplier_concentration(min_companies)

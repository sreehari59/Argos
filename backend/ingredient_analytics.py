"""
Ingredient Analytics Module:
- Identify most-used ingredients across the supply chain
- Analyze which companies use specific ingredients
- Map suppliers for each ingredient
- Identify substitution patterns
- Support batching optimization scenarios
"""
from typing import List, Dict, Any, Optional
import json

from db import query


def get_top_ingredients(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get the most frequently used ingredients across all products.
    
    Returns:
        List of ingredients with usage statistics, companies, and suppliers
    """
    # Get usage counts with company and supplier information
    ingredients = query("""
        SELECT 
            p.SKU,
            COUNT(DISTINCT bc.BOMId) as usage_count,
            COUNT(DISTINCT fp.Id) as product_count,
            COUNT(DISTINCT c.Id) as company_count,
            GROUP_CONCAT(DISTINCT c.Name) as companies_using
        FROM BOM_Component bc
        JOIN BOM b ON bc.BOMId = b.Id
        JOIN Product p ON bc.ConsumedProductId = p.Id
        JOIN Product fp ON b.ProducedProductId = fp.Id
        JOIN Company c ON fp.CompanyId = c.Id
        WHERE p.Type = 'raw-material'
        GROUP BY p.SKU
        ORDER BY usage_count DESC
        LIMIT ?
    """, (limit,))
    
    # Enrich with canonical names and suppliers
    for ing in ingredients:
        # Get canonical name from Ingredient_Family
        canonical = query("""
            SELECT DISTINCT ifam.canonical_name, ifam.family_name, ifam.family_type
            FROM Ingredient_Family ifam
            JOIN Ingredient_Family_Member ifm ON ifam.Id = ifm.family_id
            JOIN Product p ON ifm.product_id = p.Id
            WHERE p.SKU = ?
            LIMIT 1
        """, (ing['SKU'],))
        
        if canonical:
            ing['canonical_name'] = canonical[0]['canonical_name']
            ing['family_name'] = canonical[0]['family_name']
            ing['family_type'] = canonical[0]['family_type']
        else:
            ing['canonical_name'] = ing['SKU'].replace('RM-', '').split('-')[2:-1]
            ing['family_name'] = None
            ing['family_type'] = None
        
        # Get suppliers
        suppliers = query("""
            SELECT DISTINCT s.Name, s.Id
            FROM Supplier_Product sp
            JOIN Supplier s ON sp.SupplierId = s.Id
            JOIN Product p ON sp.ProductId = p.Id
            WHERE p.SKU = ?
        """, (ing['SKU'],))
        
        ing['suppliers'] = [{'id': s['Id'], 'name': s['Name']} for s in suppliers]
        ing['supplier_count'] = len(suppliers)
        
        # Parse companies_using into list
        if ing['companies_using']:
            ing['companies_list'] = ing['companies_using'].split(',')
        else:
            ing['companies_list'] = []
    
    return ingredients


def get_ingredient_details(ingredient_sku: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific ingredient.
    
    Returns:
        - Usage statistics
        - Companies using it
        - Suppliers providing it
        - Substitution alternatives
        - Functional role distribution
    """
    # Basic ingredient info
    ingredient = query("""
        SELECT p.Id, p.SKU, p.CompanyId
        FROM Product p
        WHERE p.SKU = ? AND p.Type = 'raw-material'
        LIMIT 1
    """, (ingredient_sku,))
    
    if not ingredient:
        return None
    
    ingredient = ingredient[0]
    
    # Get canonical name and family
    canonical = query("""
        SELECT DISTINCT ifam.canonical_name, ifam.family_name, ifam.family_type
        FROM Ingredient_Family ifam
        JOIN Ingredient_Family_Member ifm ON ifam.Id = ifm.family_id
        WHERE ifm.product_id = ?
    """, (ingredient['Id'],))
    
    canonical_name = canonical[0]['canonical_name'] if canonical else None
    family_name = canonical[0]['family_name'] if canonical else None
    family_type = canonical[0]['family_type'] if canonical else None
    
    # Companies using this ingredient
    companies = query("""
        SELECT DISTINCT c.Id, c.Name, COUNT(DISTINCT fp.Id) as product_count
        FROM BOM_Component bc
        JOIN BOM b ON bc.BOMId = b.Id
        JOIN Product fp ON b.ProducedProductId = fp.Id
        JOIN Company c ON fp.CompanyId = c.Id
        WHERE bc.ConsumedProductId = ?
        GROUP BY c.Id, c.Name
        ORDER BY product_count DESC
    """, (ingredient['Id'],))
    
    # Suppliers providing this ingredient
    suppliers = query("""
        SELECT DISTINCT s.Id, s.Name
        FROM Supplier_Product sp
        JOIN Supplier s ON sp.SupplierId = s.Id
        WHERE sp.ProductId = ?
    """, (ingredient['Id'],))
    
    # Get substitution alternatives from the same family
    alternatives = []
    if family_name:
        alternatives = query("""
            SELECT DISTINCT 
                ifam.canonical_name,
                ifam.family_type,
                COUNT(DISTINCT ifm.product_id) as availability_count
            FROM Ingredient_Family ifam
            JOIN Ingredient_Family_Member ifm ON ifam.Id = ifm.family_id
            WHERE ifam.family_name = ? AND ifam.canonical_name != ?
            GROUP BY ifam.canonical_name, ifam.family_type
            ORDER BY availability_count DESC
        """, (family_name, canonical_name))
        
        # For each alternative, get which companies use it
        for alt in alternatives:
            companies_using_alt = query("""
                SELECT DISTINCT c.Name
                FROM Ingredient_Family ifam
                JOIN Ingredient_Family_Member ifm ON ifam.Id = ifm.family_id
                JOIN Product p_rm ON ifm.product_id = p_rm.Id
                JOIN BOM_Component bc ON p_rm.Id = bc.ConsumedProductId
                JOIN BOM b ON bc.BOMId = b.Id
                JOIN Product fp ON b.ProducedProductId = fp.Id
                JOIN Company c ON fp.CompanyId = c.Id
                WHERE ifam.canonical_name = ?
            """, (alt['canonical_name'],))
            
            alt['companies_using'] = [c['Name'] for c in companies_using_alt]
            alt['company_count'] = len(alt['companies_using'])
    
    # Get functional roles
    try:
        roles = query("""
            SELECT DISTINCT ir.functional_role, COUNT(*) as usage_count
            FROM Ingredient_Role ir
            WHERE ir.canonical_name = ?
            GROUP BY ir.functional_role
            ORDER BY usage_count DESC
        """, (canonical_name,)) if canonical_name else []
    except Exception as e:
        # Table might not exist yet if roles haven't been generated
        roles = []
    
    return {
        'sku': ingredient_sku,
        'product_id': ingredient['Id'],
        'canonical_name': canonical_name,
        'family_name': family_name,
        'family_type': family_type,
        'companies_using': companies,
        'company_count': len(companies),
        'suppliers': suppliers,
        'supplier_count': len(suppliers),
        'alternatives': alternatives,
        'functional_roles': roles,
    }


def get_batching_opportunities(company_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Identify supplier consolidation opportunities for batching.
    
    Example scenario:
    - Company 1: Gets Vitamin A, B from Supplier Q; Vitamin C from Supplier R
    - Company 2: Gets Vitamin A from Supplier Q; Vitamin B from Supplier R
    - Recommendation: Company 2 should get Vitamin B from Supplier Q too
    
    Returns:
        List of batching opportunities with potential savings
    """
    # Get all company-ingredient-supplier relationships
    if company_id:
        relationships = query("""
            SELECT DISTINCT
                c.Id as company_id,
                c.Name as company_name,
                p_rm.Id as ingredient_id,
                p_rm.SKU as ingredient_sku,
                s.Id as current_supplier_id,
                s.Name as current_supplier_name,
                ifam.canonical_name,
                ifam.family_name
            FROM Company c
            JOIN Product fp ON c.Id = fp.CompanyId
            JOIN BOM b ON fp.Id = b.ProducedProductId
            JOIN BOM_Component bc ON b.Id = bc.BOMId
            JOIN Product p_rm ON bc.ConsumedProductId = p_rm.Id
            JOIN Supplier_Product sp ON p_rm.Id = sp.ProductId
            JOIN Supplier s ON sp.SupplierId = s.Id
            LEFT JOIN Ingredient_Family_Member ifm ON p_rm.Id = ifm.product_id
            LEFT JOIN Ingredient_Family ifam ON ifm.family_id = ifam.Id
            WHERE p_rm.Type = 'raw-material' AND c.Id = ?
            ORDER BY c.Name, ifam.canonical_name
        """, (company_id,))
    else:
        relationships = query("""
            SELECT DISTINCT
                c.Id as company_id,
                c.Name as company_name,
                p_rm.Id as ingredient_id,
                p_rm.SKU as ingredient_sku,
                s.Id as current_supplier_id,
                s.Name as current_supplier_name,
                ifam.canonical_name,
                ifam.family_name
            FROM Company c
            JOIN Product fp ON c.Id = fp.CompanyId
            JOIN BOM b ON fp.Id = b.ProducedProductId
            JOIN BOM_Component bc ON b.Id = bc.BOMId
            JOIN Product p_rm ON bc.ConsumedProductId = p_rm.Id
            JOIN Supplier_Product sp ON p_rm.Id = sp.ProductId
            JOIN Supplier s ON sp.SupplierId = s.Id
            LEFT JOIN Ingredient_Family_Member ifm ON p_rm.Id = ifm.product_id
            LEFT JOIN Ingredient_Family ifam ON ifm.family_id = ifam.Id
            WHERE p_rm.Type = 'raw-material'
            ORDER BY c.Name, ifam.canonical_name
        """)
    
    # Group by company
    company_data = {}
    for rel in relationships:
        cid = rel['company_id']
        if cid not in company_data:
            company_data[cid] = {
                'company_id': cid,
                'company_name': rel['company_name'],
                'ingredients': {},
                'suppliers': set(),
            }
        
        canonical = rel['canonical_name'] or rel['ingredient_sku']
        if canonical not in company_data[cid]['ingredients']:
            company_data[cid]['ingredients'][canonical] = {
                'canonical_name': canonical,
                'family_name': rel['family_name'],
                'current_supplier': rel['current_supplier_name'],
                'current_supplier_id': rel['current_supplier_id'],
            }
        
        company_data[cid]['suppliers'].add(rel['current_supplier_name'])
    
    # Find batching opportunities
    opportunities = []
    
    for cid, data in company_data.items():
        # For each ingredient, check if other suppliers this company uses also offer it
        for ing_name, ing_data in data['ingredients'].items():
            current_supplier = ing_data['current_supplier']
            
            # Find alternative suppliers that:
            # 1. This company already uses for other ingredients
            # 2. Also offer this ingredient or substitutes
            
            # Get all suppliers this company uses
            company_suppliers = list(data['suppliers'])
            
            # For each other supplier, check if they offer this ingredient or substitutes
            for alt_supplier in company_suppliers:
                if alt_supplier == current_supplier:
                    continue
                
                # Check if this supplier offers the same ingredient or family members
                if ing_data['family_name']:
                    # Check for family members
                    alt_availability = query("""
                        SELECT DISTINCT 
                            ifam.canonical_name,
                            s.Name as supplier_name,
                            p.SKU
                        FROM Ingredient_Family ifam
                        JOIN Ingredient_Family_Member ifm ON ifam.Id = ifm.family_id
                        JOIN Product p ON ifm.product_id = p.Id
                        JOIN Supplier_Product sp ON p.Id = sp.ProductId
                        JOIN Supplier s ON sp.SupplierId = s.Id
                        WHERE ifam.family_name = ? AND s.Name = ?
                    """, (ing_data['family_name'], alt_supplier))
                else:
                    # Check for exact ingredient
                    alt_availability = query("""
                        SELECT DISTINCT 
                            p.SKU as canonical_name,
                            s.Name as supplier_name,
                            p.SKU
                        FROM Product p
                        JOIN Supplier_Product sp ON p.Id = sp.ProductId
                        JOIN Supplier s ON sp.SupplierId = s.Id
                        WHERE p.SKU = ? AND s.Name = ?
                    """, (ing_name, alt_supplier))
                
                if alt_availability:
                    # This is a batching opportunity!
                    # Count how many other ingredients this company gets from alt_supplier
                    ingredients_from_alt = sum(
                        1 for i in data['ingredients'].values() 
                        if i['current_supplier'] == alt_supplier
                    )
                    
                    opportunities.append({
                        'company_id': cid,
                        'company_name': data['company_name'],
                        'ingredient': ing_name,
                        'current_supplier': current_supplier,
                        'recommended_supplier': alt_supplier,
                        'alternative_ingredient': alt_availability[0]['canonical_name'],
                        'batching_benefit': ingredients_from_alt,
                        'reason': f"Consolidate with {ingredients_from_alt} other ingredients already sourced from {alt_supplier}",
                    })
    
    # Sort by batching benefit (higher = more consolidation)
    opportunities.sort(key=lambda x: x['batching_benefit'], reverse=True)
    
    return opportunities


def get_company_supply_chain_health(company_id: int) -> Dict[str, Any]:
    """
    Calculate supply chain health score for a company.
    
    Factors:
    - Single-source risk (ingredients from only 1 supplier)
    - Supplier concentration (% of ingredients from top supplier)
    - Quality opportunities (organic/non-GMO upgrades available)
    - Diversification score (supplier diversity)
    
    Returns:
        Health score (0-100) with breakdown and recommendations
    """
    # Get company info
    company = query("SELECT * FROM Company WHERE Id = ?", (company_id,))[0]
    
    # Get all ingredients and their suppliers
    ingredient_suppliers = query("""
        SELECT DISTINCT
            p_rm.Id as ingredient_id,
            p_rm.SKU as ingredient_sku,
            ifam.canonical_name,
            s.Id as supplier_id,
            s.Name as supplier_name
        FROM Product fp
        JOIN BOM b ON fp.Id = b.ProducedProductId
        JOIN BOM_Component bc ON b.Id = bc.BOMId
        JOIN Product p_rm ON bc.ConsumedProductId = p_rm.Id
        JOIN Supplier_Product sp ON p_rm.Id = sp.ProductId
        JOIN Supplier s ON sp.SupplierId = s.Id
        LEFT JOIN Ingredient_Family_Member ifm ON p_rm.Id = ifm.product_id
        LEFT JOIN Ingredient_Family ifam ON ifm.family_id = ifam.Id
        WHERE fp.CompanyId = ? AND p_rm.Type = 'raw-material'
    """, (company_id,))
    
    # Group by ingredient
    ingredient_map = {}
    for rel in ingredient_suppliers:
        ing_id = rel['ingredient_id']
        if ing_id not in ingredient_map:
            ingredient_map[ing_id] = {
                'sku': rel['ingredient_sku'],
                'canonical_name': rel['canonical_name'],
                'suppliers': []
            }
        ingredient_map[ing_id]['suppliers'].append({
            'id': rel['supplier_id'],
            'name': rel['supplier_name']
        })
    
    # Calculate metrics
    total_ingredients = len(ingredient_map)
    single_source_count = sum(1 for ing in ingredient_map.values() if len(ing['suppliers']) == 1)
    
    # Supplier concentration
    supplier_counts = {}
    for ing in ingredient_map.values():
        for sup in ing['suppliers']:
            supplier_counts[sup['name']] = supplier_counts.get(sup['name'], 0) + 1
    
    if supplier_counts:
        top_supplier_count = max(supplier_counts.values())
        supplier_concentration = (top_supplier_count / total_ingredients) * 100 if total_ingredients > 0 else 0
    else:
        supplier_concentration = 0
    
    # Quality upgrade opportunities
    try:
        quality_upgrades = query("""
            SELECT COUNT(*) as count
            FROM Substitution_Candidate sc
            JOIN Product p ON sc.product_id = p.Id
            WHERE p.CompanyId = ? 
            AND sc.quality_score > 0.85
            AND sc.final_score > 0.7
        """, (company_id,))
        
        quality_upgrade_count = quality_upgrades[0]['count'] if quality_upgrades else 0
    except Exception as e:
        # Table might not exist yet if recommendations haven't been generated
        quality_upgrade_count = 0
    
    # Calculate health score (0-100)
    # Lower single-source risk = better
    # Lower supplier concentration = better
    # More quality upgrades available = opportunity (neutral to score)
    
    single_source_score = max(0, 100 - (single_source_count / total_ingredients * 100)) if total_ingredients > 0 else 100
    concentration_score = max(0, 100 - supplier_concentration)
    diversification_score = min(100, len(supplier_counts) * 10)  # More suppliers = better
    
    overall_score = (single_source_score * 0.4 + concentration_score * 0.3 + diversification_score * 0.3)
    
    return {
        'company_id': company_id,
        'company_name': company['Name'],
        'overall_score': round(overall_score, 1),
        'metrics': {
            'total_ingredients': total_ingredients,
            'total_suppliers': len(supplier_counts),
            'single_source_ingredients': single_source_count,
            'single_source_percentage': round((single_source_count / total_ingredients * 100), 1) if total_ingredients > 0 else 0,
            'top_supplier_concentration': round(supplier_concentration, 1),
            'quality_upgrade_opportunities': quality_upgrade_count,
        },
        'scores': {
            'single_source_risk': round(single_source_score, 1),
            'supplier_concentration': round(concentration_score, 1),
            'supplier_diversification': round(diversification_score, 1),
        },
        'grade': 'A' if overall_score >= 80 else 'B' if overall_score >= 60 else 'C' if overall_score >= 40 else 'D',
    }


if __name__ == "__main__":
    # Test the functions
    print("=== Top 10 Most-Used Ingredients ===")
    top = get_top_ingredients(10)
    for i, ing in enumerate(top, 1):
        print(f"{i}. {ing.get('canonical_name', ing['SKU'])}")
        print(f"   Used in {ing['usage_count']} BOMs by {ing['company_count']} companies")
        print(f"   Suppliers: {ing['supplier_count']}")
    
    print("\n=== Ingredient Details Example ===")
    if top:
        details = get_ingredient_details(top[0]['SKU'])
        if details:
            print(f"Ingredient: {details['canonical_name']}")
            print(f"Companies: {details['company_count']}")
            print(f"Suppliers: {details['supplier_count']}")
            print(f"Alternatives: {len(details['alternatives'])}")
    
    print("\n=== Batching Opportunities (Top 5) ===")
    batching = get_batching_opportunities()
    for i, opp in enumerate(batching[:5], 1):
        print(f"{i}. {opp['company_name']}: {opp['ingredient']}")
        print(f"   From {opp['current_supplier']} → {opp['recommended_supplier']}")
        print(f"   Benefit: {opp['reason']}")
    
    print("\n=== Company Health Score Example ===")
    companies = query("SELECT Id FROM Company LIMIT 1")
    if companies:
        health = get_company_supply_chain_health(companies[0]['Id'])
        print(f"Company: {health['company_name']}")
        print(f"Overall Score: {health['overall_score']}/100 (Grade: {health['grade']})")
        print(f"Metrics: {health['metrics']}")

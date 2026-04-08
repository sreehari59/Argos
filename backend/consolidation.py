"""
Consolidation Optimizer:
- Identify opportunities to consolidate suppliers
- Recommend multi-product substitutions that reduce supplier count
- Calculate cost/risk benefits of consolidation
"""
import json
from typing import Dict, Any, List, Set, Tuple
from collections import defaultdict

from db import query


# ---------------------------------------------------------------------------
# Consolidation Analysis
# ---------------------------------------------------------------------------

def find_consolidation_opportunities(company_id: int = None) -> List[Dict[str, Any]]:
    """
    Find opportunities to consolidate suppliers by recommending substitutions
    that allow sourcing from fewer suppliers.
    
    Returns list of consolidation opportunities with potential impact.
    """
    print("=== Finding Consolidation Opportunities ===")
    
    # Get all high-scoring recommendations
    if company_id:
        recommendations = query("""
            SELECT sc.*, p.CompanyId, c.Name as company_name
            FROM Substitution_Candidate sc
            JOIN Product p ON sc.product_id = p.Id
            JOIN Company c ON p.CompanyId = c.Id
            WHERE sc.final_score > 0.6 AND p.CompanyId = ?
            ORDER BY sc.final_score DESC
        """, (company_id,))
    else:
        recommendations = query("""
            SELECT sc.*, p.CompanyId, c.Name as company_name
            FROM Substitution_Candidate sc
            JOIN Product p ON sc.product_id = p.Id
            JOIN Company c ON p.CompanyId = c.Id
            WHERE sc.final_score > 0.6
            ORDER BY sc.final_score DESC
        """)
    
    print(f"Analyzing {len(recommendations)} high-quality recommendations...")
    
    # Group by company
    by_company = defaultdict(list)
    for rec in recommendations:
        by_company[rec['CompanyId']].append(rec)
    
    opportunities = []
    
    for comp_id, recs in by_company.items():
        if not recs:
            continue
        
        company_name = recs[0]['company_name']
        
        # Get current supplier diversity for this company
        current_suppliers = query("""
            SELECT DISTINCT s.Id, s.Name
            FROM Product p
            JOIN Supplier_Product sp ON p.Id = sp.ProductId
            JOIN Supplier s ON sp.SupplierId = s.Id
            WHERE p.CompanyId = ? AND p.Type = 'raw-material'
        """, (comp_id,))
        
        current_supplier_count = len(current_suppliers)
        
        # For each recommendation, check which suppliers offer the substitute
        supplier_coverage = defaultdict(list)  # supplier_id -> list of substitutions they enable
        
        for rec in recs:
            try:
                available_suppliers = json.loads(rec['available_suppliers'])
            except:
                available_suppliers = []
            
            # Get supplier IDs
            for supplier_name in available_suppliers:
                supplier_info = query(
                    "SELECT Id FROM Supplier WHERE Name = ?",
                    (supplier_name,)
                )
                if supplier_info:
                    supplier_id = supplier_info[0]['Id']
                    supplier_coverage[supplier_id].append({
                        'product_id': rec['product_id'],
                        'current': rec['current_canonical_name'],
                        'substitute': rec['substitute_canonical_name'],
                        'role': rec['functional_role'],
                        'score': rec['final_score'],
                    })
        
        # Find suppliers that enable the most consolidation
        for supplier_id, substitutions in supplier_coverage.items():
            if len(substitutions) < 2:
                continue  # Need at least 2 substitutions for consolidation
            
            supplier_info = query("SELECT Name FROM Supplier WHERE Id = ?", (supplier_id,))
            supplier_name = supplier_info[0]['Name'] if supplier_info else 'Unknown'
            
            # Calculate impact
            unique_ingredients = len(set(s['current'] for s in substitutions))
            avg_score = sum(s['score'] for s in substitutions) / len(substitutions)
            
            opportunities.append({
                'company_id': comp_id,
                'company_name': company_name,
                'supplier_id': supplier_id,
                'supplier_name': supplier_name,
                'substitution_count': len(substitutions),
                'unique_ingredients': unique_ingredients,
                'avg_score': avg_score,
                'current_supplier_count': current_supplier_count,
                'substitutions': substitutions,
            })
    
    # Sort by impact (substitution count * avg score)
    opportunities.sort(key=lambda x: x['substitution_count'] * x['avg_score'], reverse=True)
    
    print(f"\nFound {len(opportunities)} consolidation opportunities")
    
    if opportunities:
        print(f"\nTop 5 opportunities:")
        for i, opp in enumerate(opportunities[:5], 1):
            print(f"  {i}. {opp['company_name']} → {opp['supplier_name']}")
            print(f"     {opp['substitution_count']} substitutions, avg score: {opp['avg_score']:.2f}")
    
    return opportunities


def analyze_supplier_concentration(min_companies: int = 5) -> List[Dict[str, Any]]:
    """
    Analyze supplier concentration risks across the network.
    
    Returns suppliers serving many companies (concentration risk).
    """
    suppliers = query("""
        SELECT s.Id, s.Name,
               COUNT(DISTINCT p.CompanyId) as companies_served,
               COUNT(DISTINCT sp.ProductId) as materials_supplied,
               GROUP_CONCAT(DISTINCT c.Name) as company_names
        FROM Supplier s
        JOIN Supplier_Product sp ON s.Id = sp.SupplierId
        JOIN Product p ON sp.ProductId = p.Id
        JOIN Company c ON p.CompanyId = c.Id
        GROUP BY s.Id
        HAVING companies_served >= ?
        ORDER BY companies_served DESC
    """, (min_companies,))
    
    results = []
    for s in suppliers:
        # Calculate concentration risk score
        # Higher score = higher risk (more companies dependent on this supplier)
        risk_score = min(1.0, s['companies_served'] / 61.0)  # 61 total companies
        
        results.append({
            'supplier_id': s['Id'],
            'supplier_name': s['Name'],
            'companies_served': s['companies_served'],
            'materials_supplied': s['materials_supplied'],
            'concentration_risk': risk_score,
            'company_names': s['company_names'].split(',') if s['company_names'] else [],
        })
    
    return results


def recommend_diversification(company_id: int) -> Dict[str, Any]:
    """
    Recommend supplier diversification strategies for a company.
    
    Identifies single-source ingredients and suggests alternatives.
    """
    # Get ingredients with only one supplier - handle missing Ingredient_Role table
    try:
        single_source = query("""
            SELECT ir.canonical_name, ir.functional_role,
                   COUNT(DISTINCT sp.SupplierId) as supplier_count,
                   GROUP_CONCAT(DISTINCT s.Name) as supplier_names
            FROM Ingredient_Role ir
            JOIN BOM b ON ir.product_id = b.ProducedProductId
            JOIN Product p ON b.ProducedProductId = p.Id
            JOIN Supplier_Product sp ON ir.ingredient_id = sp.ProductId
            JOIN Supplier s ON sp.SupplierId = s.Id
            WHERE p.CompanyId = ?
            GROUP BY ir.canonical_name
            HAVING supplier_count = 1
        """, (company_id,))
    except:
        # Fallback without Ingredient_Role
        single_source = query("""
            SELECT ifam.canonical_name,
                   COUNT(DISTINCT sp.SupplierId) as supplier_count,
                   GROUP_CONCAT(DISTINCT s.Name) as supplier_names
            FROM Ingredient_Family ifam
            JOIN Ingredient_Family_Member ifm ON ifam.Id = ifm.family_id
            JOIN Product p_rm ON ifm.product_id = p_rm.Id
            JOIN BOM_Component bc ON p_rm.Id = bc.ConsumedProductId
            JOIN BOM b ON bc.BOMId = b.Id
            JOIN Product p_fg ON b.ProducedProductId = p_fg.Id
            JOIN Supplier_Product sp ON p_rm.Id = sp.ProductId
            JOIN Supplier s ON sp.SupplierId = s.Id
            WHERE p_fg.CompanyId = ?
            GROUP BY ifam.canonical_name
            HAVING supplier_count = 1
        """, (company_id,))
    
    recommendations = []
    
    for ing in single_source:
        # Find substitution candidates for this ingredient
        try:
            candidates = query("""
                SELECT DISTINCT sc.substitute_canonical_name, sc.available_suppliers, sc.final_score
                FROM Substitution_Candidate sc
                JOIN Product p ON sc.product_id = p.Id
                WHERE p.CompanyId = ? AND sc.current_canonical_name = ? AND sc.final_score > 0.6
                ORDER BY sc.final_score DESC
                LIMIT 3
            """, (company_id, ing['canonical_name']))
        except:
            # No substitution candidates available
            candidates = []
        
        if candidates:
            recommendations.append({
                'ingredient': ing['canonical_name'],
                'role': ing.get('functional_role', 'unknown'),
                'current_supplier': ing['supplier_names'],
                'alternatives': [
                    {
                        'substitute': c['substitute_canonical_name'],
                        'suppliers': json.loads(c['available_suppliers']) if c['available_suppliers'] else [],
                        'score': c['final_score'],
                    }
                    for c in candidates
                ],
            })
    
    return {
        'company_id': company_id,
        'single_source_count': len(single_source),
        'diversification_opportunities': len(recommendations),
        'recommendations': recommendations,
    }


if __name__ == "__main__":
    # Test consolidation analysis
    opportunities = find_consolidation_opportunities()
    
    print("\n" + "="*60)
    print("Supplier Concentration Analysis")
    print("="*60)
    
    concentration = analyze_supplier_concentration(min_companies=10)
    print(f"\nHigh-concentration suppliers (serving 10+ companies):")
    for i, sup in enumerate(concentration[:5], 1):
        print(f"  {i}. {sup['supplier_name']}: {sup['companies_served']} companies, {sup['materials_supplied']} materials")
        print(f"     Risk score: {sup['concentration_risk']:.2f}")

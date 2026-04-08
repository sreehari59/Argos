"""
Recommendation Engine:
- Generate substitution candidates (same family + same functional role)
- Score by quality, compliance, and ingredient priority
- Store recommendations with evidence trails
"""
import json
from typing import List, Dict, Any, Optional, Tuple

from db import query, execute, executemany, execute_script
from graph import get_graph


# ---------------------------------------------------------------------------
# Step 2.1: Substitution Candidate Generator
# ---------------------------------------------------------------------------

def create_tables():
    """Create tables for storing recommendations."""
    execute_script("""
        CREATE TABLE IF NOT EXISTS Substitution_Candidate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            current_ingredient_id INTEGER NOT NULL,
            current_canonical_name TEXT NOT NULL,
            substitute_ingredient_id INTEGER,
            substitute_canonical_name TEXT NOT NULL,
            family_name TEXT NOT NULL,
            family_type TEXT NOT NULL,
            functional_role TEXT NOT NULL,
            available_suppliers TEXT,
            priority_rank REAL DEFAULT 0.5,
            quality_score REAL,
            compliance_score REAL,
            final_score REAL,
            quality_reasoning TEXT,
            compliance_reasoning TEXT,
            confidence TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES Product(Id),
            FOREIGN KEY (current_ingredient_id) REFERENCES Product(Id)
        );

        CREATE INDEX IF NOT EXISTS idx_sub_product ON Substitution_Candidate(product_id);
        CREATE INDEX IF NOT EXISTS idx_sub_current ON Substitution_Candidate(current_ingredient_id);
    """)


def get_substitution_candidates_for_product(product_id: int) -> List[Dict[str, Any]]:
    """
    Generate substitution candidates for all ingredients in a product.
    
    Criteria:
    1. Same ingredient family (from Ingredient_Family)
    2. Same functional role (from Ingredient_Role)
    3. Different canonical name (actual substitution)
    4. Has supplier availability
    """
    # Get all ingredients in this product with their roles and families
    current_ingredients = query("""
        SELECT ir.ingredient_id, ir.canonical_name, ir.functional_role,
               ifam.family_name, ifam.family_type
        FROM Ingredient_Role ir
        JOIN Ingredient_Family ifam ON ir.canonical_name = ifam.canonical_name
        WHERE ir.product_id = ?
    """, (product_id,))

    candidates = []

    for current in current_ingredients:
        # Find other canonical names in the same family
        family_members = query("""
            SELECT DISTINCT canonical_name
            FROM Ingredient_Family
            WHERE family_name = ? AND canonical_name != ?
        """, (current['family_name'], current['canonical_name']))

        for member in family_members:
            substitute_name = member['canonical_name']
            
            # Check if this substitute has the same functional role in other products
            # (ensures it's actually used for the same purpose)
            role_check = query("""
                SELECT COUNT(*) as count
                FROM Ingredient_Role
                WHERE canonical_name = ? AND functional_role = ?
            """, (substitute_name, current['functional_role']))
            
            if role_check[0]['count'] == 0:
                # This substitute isn't used in the same role anywhere, skip
                continue

            # Find suppliers for this substitute
            # Get product IDs that match this canonical name
            substitute_products = query("""
                SELECT DISTINCT ifm.product_id
                FROM Ingredient_Family ifam
                JOIN Ingredient_Family_Member ifm ON ifam.Id = ifm.family_id
                WHERE ifam.canonical_name = ?
            """, (substitute_name,))

            if not substitute_products:
                continue

            substitute_product_ids = [p['product_id'] for p in substitute_products]
            
            # Get suppliers
            placeholders = ','.join('?' * len(substitute_product_ids))
            suppliers = query(f"""
                SELECT DISTINCT s.Name
                FROM Supplier_Product sp
                JOIN Supplier s ON sp.SupplierId = s.Id
                WHERE sp.ProductId IN ({placeholders})
            """, tuple(substitute_product_ids))

            if not suppliers:
                # No supplier offers this substitute
                continue

            supplier_names = [s['Name'] for s in suppliers]

            # Get priority rank for the current ingredient from enrichment data
            priority_rank = 0.5  # default
            try:
                enrichment = query("""
                    SELECT ingredient_priority_json
                    FROM Clean_Enrichment
                    WHERE product_id = ?
                """, (product_id,))
                
                if enrichment and enrichment[0]['ingredient_priority_json']:
                    try:
                        ing_list = json.loads(enrichment[0]['ingredient_priority_json'])
                        # Try to match current ingredient to label position
                        for i, label_ing in enumerate(ing_list):
                            if current['canonical_name'].replace('-', ' ').lower() in label_ing.lower():
                                priority_rank = 1.0 / (i + 1)
                                break
                    except (json.JSONDecodeError, TypeError):
                        pass
            except:
                # Clean_Enrichment table doesn't exist, use default priority
                pass

            candidates.append({
                'product_id': product_id,
                'current_ingredient_id': current['ingredient_id'],
                'current_canonical_name': current['canonical_name'],
                'substitute_ingredient_id': substitute_product_ids[0] if substitute_product_ids else None,
                'substitute_canonical_name': substitute_name,
                'family_name': current['family_name'],
                'family_type': current['family_type'],
                'functional_role': current['functional_role'],
                'available_suppliers': json.dumps(supplier_names),
                'priority_rank': priority_rank,
            })

    return candidates


def generate_all_candidates():
    """Generate substitution candidates for all products."""
    print("=== Generating Substitution Candidates ===")
    
    create_tables()
    
    # Get all finished goods
    products = query("SELECT Id FROM Product WHERE Type = 'finished-good'")
    print(f"Processing {len(products)} products...")

    all_candidates = []
    product_counts = {}

    for p in products:
        candidates = get_substitution_candidates_for_product(p['Id'])
        all_candidates.extend(candidates)
        if candidates:
            product_counts[p['Id']] = len(candidates)

    print(f"\nGenerated {len(all_candidates)} substitution candidates")
    print(f"Products with candidates: {len(product_counts)}")
    
    if product_counts:
        avg = sum(product_counts.values()) / len(product_counts)
        max_prod = max(product_counts, key=product_counts.get)
        print(f"Average per product: {avg:.1f}")
        print(f"Max: {product_counts[max_prod]} (product {max_prod})")

    # Save to database
    if all_candidates:
        # Clear existing
        execute("DELETE FROM Substitution_Candidate")
        
        # Insert new
        rows = []
        for c in all_candidates:
            rows.append((
                c['product_id'],
                c['current_ingredient_id'],
                c['current_canonical_name'],
                c.get('substitute_ingredient_id'),
                c['substitute_canonical_name'],
                c['family_name'],
                c['family_type'],
                c['functional_role'],
                c['available_suppliers'],
                c['priority_rank'],
            ))
        
        executemany("""
            INSERT INTO Substitution_Candidate (
                product_id, current_ingredient_id, current_canonical_name,
                substitute_ingredient_id, substitute_canonical_name,
                family_name, family_type, functional_role,
                available_suppliers, priority_rank
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        
        print(f"Saved to database.")

    # Stats by family type
    by_type = {}
    for c in all_candidates:
        ft = c['family_type']
        by_type[ft] = by_type.get(ft, 0) + 1
    
    print(f"\nBy family type:")
    for ft, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {ft}: {count}")

    # Stats by functional role
    by_role = {}
    for c in all_candidates:
        role = c['functional_role']
        by_role[role] = by_role.get(role, 0) + 1
    
    print(f"\nTop 10 roles with substitution opportunities:")
    for role, count in sorted(by_role.items(), key=lambda x: -x[1])[:10]:
        print(f"  {role}: {count}")

    return all_candidates


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def get_recommendations_for_product(product_id: int) -> List[Dict[str, Any]]:
    """Get all recommendations for a product, sorted by final score."""
    recs = query("""
        SELECT *
        FROM Substitution_Candidate
        WHERE product_id = ?
        ORDER BY final_score DESC NULLS LAST, priority_rank DESC
    """, (product_id,))
    
    # Parse JSON fields
    for r in recs:
        if r['available_suppliers']:
            try:
                r['available_suppliers'] = json.loads(r['available_suppliers'])
            except (json.JSONDecodeError, TypeError):
                r['available_suppliers'] = []
    
    return recs


def get_top_recommendations(limit: int = 50) -> List[Dict[str, Any]]:
    """Get top recommendations across all products."""
    try:
        recs = query("""
            SELECT sc.*, p.SKU as product_sku, c.Name as company_name
            FROM Substitution_Candidate sc
            JOIN Product p ON sc.product_id = p.Id
            JOIN Company c ON p.CompanyId = c.Id
            WHERE sc.final_score IS NOT NULL
            ORDER BY sc.final_score DESC
            LIMIT ?
        """, (limit,))
        
        for r in recs:
            if r['available_suppliers']:
                try:
                    r['available_suppliers'] = json.loads(r['available_suppliers'])
                except (json.JSONDecodeError, TypeError):
                    r['available_suppliers'] = []
        
        return recs
    except:
        # Table doesn't exist yet - return empty list
        return []


if __name__ == "__main__":
    generate_all_candidates()

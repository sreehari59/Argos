"""
Clean Enrichment Data:
- Merge Product_Enrichment (SQLite) + enriched_products.json
- Parse dietary claims -> boolean flags
- Parse allergens -> structured flags
- Parse IngredientsRaw -> ordered ingredient list with priority ranks
- Store in Clean_Enrichment table
"""
import json
import re
from pathlib import Path
from typing import Optional, List

from db import get_connection, query, execute_script

JSON_PATH = Path(__file__).parent.parent / "enriched_products.json"


# ---------------------------------------------------------------------------
# Table creation
# ---------------------------------------------------------------------------

def create_tables():
    execute_script("""
        CREATE TABLE IF NOT EXISTS Clean_Enrichment (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT,
            source TEXT,
            is_gluten_free INTEGER DEFAULT 0,
            is_non_gmo INTEGER DEFAULT 0,
            is_vegan INTEGER DEFAULT 0,
            is_vegetarian INTEGER DEFAULT 0,
            is_organic INTEGER DEFAULT 0,
            is_kosher INTEGER DEFAULT 0,
            is_dairy_free INTEGER DEFAULT 0,
            contains_soy INTEGER DEFAULT 0,
            contains_dairy INTEGER DEFAULT 0,
            contains_gluten INTEGER DEFAULT 0,
            contains_tree_nuts INTEGER DEFAULT 0,
            contains_eggs INTEGER DEFAULT 0,
            contains_fish INTEGER DEFAULT 0,
            contains_shellfish INTEGER DEFAULT 0,
            ingredient_priority_json TEXT,
            FOREIGN KEY (product_id) REFERENCES Product(Id)
        );
    """)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_dietary_claims(claims) -> dict:
    """Parse dietary claims into boolean flags."""
    flags = {
        'is_gluten_free': False,
        'is_non_gmo': False,
        'is_vegan': False,
        'is_vegetarian': False,
        'is_organic': False,
        'is_kosher': False,
        'is_dairy_free': False,
    }
    if not claims:
        return flags

    # Handle string (from SQLite) or list (from JSON)
    if isinstance(claims, str):
        try:
            claims = json.loads(claims)
        except json.JSONDecodeError:
            claims = [c.strip() for c in claims.split(',')]

    if not isinstance(claims, list):
        return flags

    text = ' '.join(c.lower() for c in claims)
    if 'gluten-free' in text or 'gluten free' in text:
        flags['is_gluten_free'] = True
    if 'non-gmo' in text or 'non gmo' in text:
        flags['is_non_gmo'] = True
    if 'vegan' in text:
        flags['is_vegan'] = True
    if 'vegetarian' in text:
        flags['is_vegetarian'] = True
    if 'organic' in text:
        flags['is_organic'] = True
    if 'kosher' in text:
        flags['is_kosher'] = True
    if 'dairy-free' in text or 'dairy free' in text:
        flags['is_dairy_free'] = True
    return flags


def parse_allergens_contains(allergens) -> dict:
    """Parse allergen_contains into boolean flags."""
    flags = {
        'contains_soy': False,
        'contains_dairy': False,
        'contains_gluten': False,
        'contains_tree_nuts': False,
        'contains_eggs': False,
        'contains_fish': False,
        'contains_shellfish': False,
    }
    if not allergens:
        return flags

    if isinstance(allergens, str):
        try:
            allergens = json.loads(allergens)
        except json.JSONDecodeError:
            allergens = [a.strip() for a in allergens.split(',')]

    if not isinstance(allergens, list):
        return flags

    text = ' '.join(a.lower() for a in allergens)
    if 'soy' in text:
        flags['contains_soy'] = True
    if 'milk' in text or 'dairy' in text or 'whey' in text or 'casein' in text:
        flags['contains_dairy'] = True
    if 'wheat' in text or 'gluten' in text:
        flags['contains_gluten'] = True
    if 'tree nut' in text or 'almond' in text or 'cashew' in text:
        flags['contains_tree_nuts'] = True
    if 'egg' in text:
        flags['contains_eggs'] = True
    if 'fish' in text:
        flags['contains_fish'] = True
    if 'shellfish' in text or 'crustacean' in text:
        flags['contains_shellfish'] = True
    return flags


def parse_allergens_free_from(allergens) -> dict:
    """Parse allergen_free_from to reinforce dietary flags."""
    updates = {}
    if not allergens:
        return updates

    if isinstance(allergens, str):
        try:
            allergens = json.loads(allergens)
        except json.JSONDecodeError:
            allergens = [a.strip() for a in allergens.split(',')]

    if not isinstance(allergens, list):
        return updates

    text = ' '.join(a.lower() for a in allergens)
    if 'soy' in text:
        updates['contains_soy'] = False
    if 'dairy' in text or 'milk' in text:
        updates['is_dairy_free'] = True
        updates['contains_dairy'] = False
    if 'gluten' in text:
        updates['is_gluten_free'] = True
        updates['contains_gluten'] = False
    return updates


def parse_ingredients_raw(raw_text: str) -> Optional[List[str]]:
    """
    Extract ordered ingredient list from raw text.
    Returns list of ingredient names in label order, or None if unparseable.
    """
    if not raw_text or len(raw_text) < 20:
        return None

    # Try to find "Ingredients" section in the text
    # Common patterns: "Ingredients: ...", "Ingredients ...", after "Ingredients" header
    text = raw_text

    # Look for ingredient list after "Ingredients" keyword
    match = re.search(r'(?:Ingredients[:\s]+)(.*?)(?:(?:Legal Disclaimer|Directions|Warnings|Storage|Important|$))',
                       text, re.IGNORECASE | re.DOTALL)
    if match:
        ingredients_text = match.group(1).strip()
    else:
        # If no clear section, check if the whole text looks like an ingredient list
        if ',' in text and len(text) < 2000:
            ingredients_text = text
        else:
            return None

    # Skip if it's just boilerplate
    if len(ingredients_text) < 10:
        return None
    if 'evaluated by the FDA' in ingredients_text:
        return None
    if ingredients_text.startswith('Vitamins & Supplements'):
        return None

    # Clean up: remove parenthetical sub-ingredients for top-level ordering
    # But keep the main ingredient names
    # Split by comma, clean each
    ingredients = []
    # Handle nested parentheses by tracking depth
    depth = 0
    current = []
    for char in ingredients_text:
        if char == '(':
            depth += 1
            current.append(char)
        elif char == ')':
            depth -= 1
            current.append(char)
        elif char == ',' and depth == 0:
            ingredient = ''.join(current).strip()
            if ingredient and len(ingredient) > 1:
                # Clean: remove leading/trailing periods, numbers
                ingredient = re.sub(r'^[\d.]+\s*', '', ingredient)
                ingredient = ingredient.strip('. ')
                if ingredient:
                    ingredients.append(ingredient)
            current = []
        else:
            current.append(char)

    # Don't forget the last ingredient
    last = ''.join(current).strip()
    if last and len(last) > 1:
        last = re.sub(r'^[\d.]+\s*', '', last)
        last = last.strip('. ')
        if last:
            ingredients.append(last)

    if len(ingredients) < 2:
        return None

    return ingredients


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_sqlite_enrichment() -> dict[int, dict]:
    """Load enrichment data from Product_Enrichment table."""
    rows = query("""
        SELECT pe.ProductId, pe.ProductName, pe.Certifications,
               pe.DietaryClaims, pe.AllergenContains, pe.AllergenFreeFrom,
               pe.IngredientsRaw
        FROM Product_Enrichment pe
    """)
    result = {}
    for row in rows:
        product_id = row['ProductId']
        dietary = parse_dietary_claims(row['DietaryClaims'])
        allergens = parse_allergens_contains(row['AllergenContains'])
        free_from = parse_allergens_free_from(row['AllergenFreeFrom'])

        # Merge flags
        flags = {**dietary, **allergens}
        flags.update(free_from)  # free_from overrides

        ingredients = parse_ingredients_raw(row['IngredientsRaw'] or '')

        result[product_id] = {
            'product_id': product_id,
            'product_name': row['ProductName'],
            'source': 'sqlite_enrichment',
            **flags,
            'ingredient_priority_json': json.dumps(ingredients) if ingredients else None,
        }
    return result


def sku_to_product_id() -> dict[str, int]:
    """Build lookup from SKU -> Product Id for finished goods."""
    rows = query("SELECT Id, SKU FROM Product WHERE Type = 'finished-good'")
    return {row['SKU']: row['Id'] for row in rows}


def load_json_enrichment() -> dict[int, dict]:
    """Load enrichment data from enriched_products.json."""
    if not JSON_PATH.exists():
        print(f"  enriched_products.json not found at {JSON_PATH}")
        return {}

    with open(JSON_PATH) as f:
        data = json.load(f)

    sku_lookup = sku_to_product_id()
    result = {}

    for entry in data:
        if not entry.get('scrape_success'):
            continue

        sku = entry.get('sku', '')
        product_id = sku_lookup.get(sku)
        if not product_id:
            continue

        dietary = parse_dietary_claims(entry.get('dietary_claims'))
        allergens = parse_allergens_contains(entry.get('allergen_contains'))
        free_from = parse_allergens_free_from(entry.get('allergen_free_from'))

        flags = {**dietary, **allergens}
        flags.update(free_from)

        ingredients = parse_ingredients_raw(entry.get('ingredients_raw') or '')

        result[product_id] = {
            'product_id': product_id,
            'product_name': entry.get('product_name'),
            'source': entry.get('source', 'json'),
            **flags,
            'ingredient_priority_json': json.dumps(ingredients) if ingredients else None,
        }

    return result


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def clean_all():
    """Run the full enrichment cleaning pipeline."""
    print("=== Clean Enrichment Data ===")

    # 1. Load from both sources
    sqlite_data = load_sqlite_enrichment()
    print(f"Loaded {len(sqlite_data)} from Product_Enrichment (SQLite)")

    json_data = load_json_enrichment()
    print(f"Loaded {len(json_data)} from enriched_products.json")

    # 2. Merge: JSON takes precedence for product_name (often better),
    #    but SQLite has richer ingredient data. Merge intelligently.
    merged = {}
    all_ids = set(sqlite_data.keys()) | set(json_data.keys())

    for pid in all_ids:
        s = sqlite_data.get(pid, {})
        j = json_data.get(pid, {})

        if s and j:
            # Merge: prefer JSON for product name, prefer whichever has more flags
            entry = {**s}
            if j.get('product_name'):
                entry['product_name'] = j['product_name']
            # OR dietary/allergen flags (union of evidence)
            for key in ['is_gluten_free', 'is_non_gmo', 'is_vegan', 'is_vegetarian',
                        'is_organic', 'is_kosher', 'is_dairy_free']:
                entry[key] = s.get(key, False) or j.get(key, False)
            for key in ['contains_soy', 'contains_dairy', 'contains_gluten',
                        'contains_tree_nuts', 'contains_eggs', 'contains_fish',
                        'contains_shellfish']:
                entry[key] = s.get(key, False) or j.get(key, False)
            # Prefer SQLite ingredient list if available (usually richer)
            if not entry.get('ingredient_priority_json') and j.get('ingredient_priority_json'):
                entry['ingredient_priority_json'] = j['ingredient_priority_json']
            entry['source'] = 'merged'
            merged[pid] = entry
        elif s:
            merged[pid] = s
        else:
            merged[pid] = j

    print(f"Merged total: {len(merged)} enriched products")

    # 3. Write to database
    create_tables()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM Clean_Enrichment")
        for pid, entry in merged.items():
            conn.execute("""
                INSERT INTO Clean_Enrichment (
                    product_id, product_name, source,
                    is_gluten_free, is_non_gmo, is_vegan, is_vegetarian,
                    is_organic, is_kosher, is_dairy_free,
                    contains_soy, contains_dairy, contains_gluten,
                    contains_tree_nuts, contains_eggs, contains_fish, contains_shellfish,
                    ingredient_priority_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.get('product_id'),
                entry.get('product_name'),
                entry.get('source'),
                int(entry.get('is_gluten_free', False)),
                int(entry.get('is_non_gmo', False)),
                int(entry.get('is_vegan', False)),
                int(entry.get('is_vegetarian', False)),
                int(entry.get('is_organic', False)),
                int(entry.get('is_kosher', False)),
                int(entry.get('is_dairy_free', False)),
                int(entry.get('contains_soy', False)),
                int(entry.get('contains_dairy', False)),
                int(entry.get('contains_gluten', False)),
                int(entry.get('contains_tree_nuts', False)),
                int(entry.get('contains_eggs', False)),
                int(entry.get('contains_fish', False)),
                int(entry.get('contains_shellfish', False)),
                entry.get('ingredient_priority_json'),
            ))
        conn.commit()

        # Stats
        total = conn.execute("SELECT COUNT(*) FROM Clean_Enrichment").fetchone()[0]
        with_ingredients = conn.execute(
            "SELECT COUNT(*) FROM Clean_Enrichment WHERE ingredient_priority_json IS NOT NULL"
        ).fetchone()[0]
        gluten_free = conn.execute(
            "SELECT COUNT(*) FROM Clean_Enrichment WHERE is_gluten_free = 1"
        ).fetchone()[0]
        non_gmo = conn.execute(
            "SELECT COUNT(*) FROM Clean_Enrichment WHERE is_non_gmo = 1"
        ).fetchone()[0]

        print(f"\nSaved to database:")
        print(f"  Total enriched: {total}")
        print(f"  With ingredient order: {with_ingredients}")
        print(f"  Gluten-free: {gluten_free}")
        print(f"  Non-GMO: {non_gmo}")

    finally:
        conn.close()

    return merged


if __name__ == "__main__":
    clean_all()

"""
Ingredient Identity Resolution:
- Parse raw material SKUs to extract canonical ingredient names
- Group into families: exact_match, form_variant, functional_substitute
- Store results in Ingredient_Family and Ingredient_Family_Member tables
"""
import re
import sqlite3
from collections import defaultdict
from difflib import SequenceMatcher

from db import get_connection, query, execute_script

# ---------------------------------------------------------------------------
# SKU Parsing
# ---------------------------------------------------------------------------

def parse_ingredient_name(sku: str) -> str:
    """
    Extract canonical ingredient name from SKU.
    SKU format: RM-C{company_id}-{ingredient-name}-{8char-hash}
    Example: RM-C30-magnesium-stearate-201fdf47 -> magnesium-stearate
    """
    # Remove the RM-C{N}- prefix
    without_prefix = re.sub(r'^RM-C\d+-', '', sku)
    # Remove the trailing -[hex hash] (8 hex chars at end)
    without_hash = re.sub(r'-[a-f0-9]{8}$', '', without_prefix)
    return without_hash


def get_all_raw_materials() -> list[dict]:
    """Fetch all raw materials with their parsed ingredient names."""
    rows = query("""
        SELECT p.Id, p.SKU, p.CompanyId, c.Name as CompanyName
        FROM Product p
        JOIN Company c ON p.CompanyId = c.Id
        WHERE p.Type = 'raw-material'
        ORDER BY p.SKU
    """)
    for row in rows:
        row['canonical_name'] = parse_ingredient_name(row['SKU'])
    return rows


# ---------------------------------------------------------------------------
# Grouping: exact matches (same canonical name across companies)
# ---------------------------------------------------------------------------

def group_exact_matches(materials: list[dict]) -> dict[str, list[dict]]:
    """Group materials by their canonical ingredient name."""
    groups = defaultdict(list)
    for m in materials:
        groups[m['canonical_name']].append(m)
    return dict(groups)


# ---------------------------------------------------------------------------
# Family detection: form variants and functional substitutes
# ---------------------------------------------------------------------------

# Known form variant families: ingredients that are the same base substance
# but in different chemical forms
FORM_VARIANT_FAMILIES = {
    'vitamin-d': [
        'vitamin-d', 'vitamin-d3', 'vitamin-d3-cholecalciferol',
        'cholecalciferol-vitamin-d3', 'cholecalciferol',
    ],
    'vitamin-c': [
        'vitamin-c', 'vitamin-c-ascorbic-acid', 'vitamin-c-l-ascorbic-acid',
        'vitamin-c-calcium-ascorbate', 'ascorbic-acid',
        'ascorbic-acid-vitamin-c', 'sodium-ascorbate', 'ascorbyl-palmitate',
        'calcium-ascorbate',
    ],
    'vitamin-a': [
        'vitamin-a', 'vitamin-a-acetate', 'vitamin-a-palmitate',
        'vitamin-a-retinyl-palmitate', 'retinyl-palmitate-vitamin-a',
        'retinyl-acetate', 'beta-carotene',
    ],
    'vitamin-e': [
        'vitamin-e', 'vitamin-e-alpha-tocopherol', 'vitamin-e-d-alpha-tocopheryl',
        'd-alpha-tocopheryl-acetate-vitamin-e', 'd-alpha-tocopheryl-succinate',
        'dl-alpha-tocopherol', 'dl-alpha-tocopheryl-acetate', 'tocopherols',
    ],
    'vitamin-b6': [
        'vitamin-b6', 'vitamin-b6-pyridoxine-hydrochloride',
        'vitamin-b6-pyridoxal-5-phosphate', 'pyridoxine-hcl',
        'pyridoxine-hydrochloride', 'pyridoxine-hydrochloride-vitamin-b6',
    ],
    'vitamin-b12': [
        'vitamin-b12', 'vitamin-b12-cyanocobalamin', 'vitamin-b12-methylcobalamin',
        'cyanocobalamin', 'cyanocobalamin-vitamin-b12',
    ],
    'vitamin-b5': [
        'pantothenic-acid', 'd-calcium-pantothenate', 'calcium-d-pantothenate',
        'calcium-pantothenate-vitamin-b5', 'vitamin-b5-d-calcium-pantothenate',
    ],
    'vitamin-b3': [
        'niacin', 'niacinamide', 'niacinamide-vitamin-b3', 'nicotinamide',
        'vitamin-b3-niacinamide',
    ],
    'vitamin-b1': [
        'thiamin', 'thiamine', 'thiamine-hcl', 'thiamine-mononitrate', 'vitamin-b1',
    ],
    'vitamin-b2': [
        'riboflavin', 'vitamin-b2',
    ],
    'vitamin-k': [
        'vitamin-k', 'vitamin-k1', 'vitamin-k2', 'vitamin-k2-menaquinone-7',
        'phytonadione',
    ],
    'magnesium-forms': [
        'magnesium', 'magnesium-oxide', 'magnesium-citrate', 'magnesium-glycinate',
        'magnesium-bisglycinate', 'magnesium-malate', 'magnesium-carbonate',
        'magnesium-taurate', 'magnesium-taurinate', 'magnesium-aspartate',
        'magnesium-l-threonate-magtein', 'magnesium-amino-acid-chelate',
        'magnesium-dimagnesium-malate', 'aquamin-mg-soluble',
    ],
    'calcium-forms': [
        'calcium', 'calcium-carbonate', 'calcium-citrate',
        'tricalcium-phosphate', 'dicalcium-phosphate',
        'dibasic-calcium-phosphate-dihydrate', 'calcium-lactate-gluconate',
        'boron-calcium-fructoborate',
    ],
    'zinc-forms': [
        'zinc', 'zinc-oxide', 'zinc-citrate', 'zinc-sulfate',
        'zinc-chelate', 'zinc-zinc-bisglycinate',
    ],
    'iron-forms': [
        'iron', 'ferrous-fumarate', 'iron-glycinate',
    ],
    'chromium-forms': [
        'chromium', 'chromium-chloride', 'chromium-nicotinate', 'chromium-picolinate',
    ],
    'whey-protein': [
        'whey-protein-isolate', 'whey-protein-concentrate',
        'hydrolyzed-whey-protein', 'organic-whey-protein',
        'grass-fed-whey-protein-concentrate', 'organic-dairy-whey-protein-concentrate',
    ],
    'gelatin-capsule': [
        'gelatin', 'gelatin-capsule', 'gelatin-capsule-bovine',
        'soft-gel-capsule-bovine-gelatin', 'softgel-bovine-gelatin',
        'softgel-capsule-bovine-gelatin', 'bone-gelatin-bovine',
    ],
    'cellulose-forms': [
        'cellulose', 'cellulose-gel', 'cellulose-gum',
        'microcrystalline-cellulose', 'vegetable-cellulose',
        'modified-cellulose', 'carboxymethylcellulose-sodium',
    ],
    'capsule-shells': [
        'hypromellose', 'hypromellose-capsule',
        'hydroxypropyl-methylcellulose', 'hydroxypropylmethylcellulose',
        'hydroxypropyl-methyl-cellulose',
        'vegan-capsule', 'vegan-capsule-hypromellose',
        'vegetarian-capsule', 'plantgel-capsule',
    ],
    'stevia-sweeteners': [
        'stevia', 'stevia-leaf-extract', 'stevia-leaf-extract-rebaudioside-a',
        'organic-stevia', 'organic-stevia-extract', 'organic-stevia-extract-leaf',
        'organic-stevia-leaf-extract-rebaudioside-a', 'rebaudioside-a',
    ],
    'coating-agents': [
        'aqueous-coating', 'organic-coating', 'pharmaceutical-glaze',
        'lac-resin', 'non-gmo-corn-zein',
    ],
}

# Known functional substitute pairs: different substances but same function
FUNCTIONAL_SUBSTITUTE_GROUPS = {
    'lecithin-emulsifiers': [
        'soy-lecithin', 'sunflower-lecithin', 'organic-sunflower-lecithin', 'lecithin',
    ],
    'artificial-sweeteners': [
        'sucralose', 'acesulfame-potassium', 'stevia-or-sucralose-sweetener',
    ],
    'natural-sugars': [
        'sugar', 'sucrose', 'cane-sugar', 'pure-cane-sugar', 'organic-cane-sugar',
        'coconut-sugar', 'dextrose', 'anhydrous-dextrose', 'glucose',
    ],
    'protein-sources': [
        'pea-protein', 'rice-protein', 'brown-rice-protein',
        'hemp-seed-protein', 'pumpkin-seed-protein', 'collagen-peptides',
        'milk-protein',
    ],
    'carrier-oils': [
        'soybean-oil', 'sunflower-oil', 'safflower-oil', 'coconut-mct-oil',
        'medium-chain-triglycerides', 'medium-chain-triglycerides-mct-from-coconut-oil',
        'olive-oil', 'palm-oil', 'corn-oil',
    ],
    'lubricants': [
        'magnesium-stearate', 'vegetable-magnesium-stearate',
        'stearic-acid', 'vegetable-stearic-acid',
    ],
    'anti-caking': [
        'silicon-dioxide', 'silica', 'sodium-aluminum-silicate', 'talc',
    ],
    'gelling-thickeners': [
        'xanthan-gum', 'gellan-gum', 'gum-arabic', 'gum-acacia',
        'organic-gum-acacia', 'acacia-gum', 'carrageenan',
    ],
    'natural-flavors': [
        'natural-flavor', 'natural-flavors', 'other-natural-flavors',
        'natural-vanilla', 'natural-vanilla-flavor', 'natural-french-vanilla-flavor',
        'ground-vanilla-beans', 'natural-cherry-flavor', 'natural-strawberry-flavor',
        'natural-peach-flavor', 'natural-lemon-lime-flavor',
        'natural-tangerine-flavor', 'natural-passionfruit-flavor',
        'orange-flavor', 'organic-vanilla-flavors', 'organic-flavor',
    ],
    'artificial-flavors': [
        'artificial-flavor', 'artificial-flavors', 'natural-and-artificial-flavors',
    ],
    'colorings': [
        'titanium-dioxide', 'blue-2-lake', 'fd-and-c-blue-no-2-lake',
        'fd-and-c-red-no-40-lake', 'fd-and-c-yellow-no-6-lake',
        'red-40-lake', 'yellow-6-lake', 'beet-extract', 'beet-juice-powder',
        'beet-powder', 'coloring-concentrates', 'fruit-and-vegetable-juice',
    ],
    'disintegrants': [
        'croscarmellose-sodium', 'sodium-starch-glycolate',
        'polyvinylpolypyrrolidone',
    ],
    'salt-forms': [
        'salt', 'salt-sodium-chloride', 'sodium-chloride', 'sea-salt',
        'pink-himalayan-salt', 'kalahari-desert-salt',
    ],
    'maltodextrin-fillers': [
        'maltodextrin', 'organic-maltodextrin', 'modified-food-starch',
        'starch', 'pea-starch',
    ],
    'preservatives': [
        'bht', 'sorbic-acid', 'sodium-benzoate', 'tocopherols',
    ],
    'prebiotic-fibers': [
        'inulin', 'organic-inulin', 'organic-agave-inulin-powder',
        'blue-agave-inulin', 'fructooligosaccharides',
        'organic-tapioca-fiber-imo', 'prebiotic-fiber', 'polydextrose',
    ],
    'potassium-forms': [
        'potassium', 'potassium-chloride', 'potassium-citrate',
        'potassium-gluconate', 'potassium-phosphate', 'potassium-aspartate',
        'dipotassium-phosphate', 'potassium-alginate',
    ],
    'sodium-forms': [
        'sodium', 'sodium-citrate',
    ],
    'manganese-forms': [
        'manganese', 'manganese-chelate', 'manganese-citrate', 'manganese-sulfate',
    ],
    'glycerin-forms': [
        'glycerin', 'vegetable-glycerin',
    ],
    'acid-buffers': [
        'citric-acid', 'non-gmo-citric-acid', 'malic-acid',
        'dl-tartaric-acid', 'lactic-acid',
    ],
}


def build_family_lookup() -> dict[str, tuple[str, str]]:
    """
    Build a lookup: ingredient_name -> (family_name, family_type)
    family_type is 'form_variant' or 'functional_substitute'
    """
    lookup = {}
    for family_name, members in FORM_VARIANT_FAMILIES.items():
        for member in members:
            lookup[member] = (family_name, 'form_variant')
    for family_name, members in FUNCTIONAL_SUBSTITUTE_GROUPS.items():
        for member in members:
            if member not in lookup:  # form_variant takes precedence
                lookup[member] = (family_name, 'functional_substitute')
    return lookup


# ---------------------------------------------------------------------------
# Main resolution pipeline
# ---------------------------------------------------------------------------

def create_tables():
    """Create the Ingredient_Family and related tables."""
    execute_script("""
        CREATE TABLE IF NOT EXISTS Ingredient_Family (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_name TEXT NOT NULL,
            family_name TEXT NOT NULL,
            family_type TEXT NOT NULL CHECK (family_type IN ('exact_match', 'form_variant', 'functional_substitute')),
            UNIQUE(canonical_name, family_name)
        );

        CREATE TABLE IF NOT EXISTS Ingredient_Family_Member (
            family_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            canonical_name TEXT NOT NULL,
            company_id INTEGER NOT NULL,
            PRIMARY KEY (family_id, product_id),
            FOREIGN KEY (family_id) REFERENCES Ingredient_Family(Id),
            FOREIGN KEY (product_id) REFERENCES Product(Id)
        );
    """)


def resolve_all():
    """Run the full ingredient identity resolution pipeline."""
    print("=== Ingredient Identity Resolution ===")

    # 1. Parse all raw materials
    materials = get_all_raw_materials()
    print(f"Parsed {len(materials)} raw materials")

    # 2. Group by canonical name (exact matches)
    exact_groups = group_exact_matches(materials)
    print(f"Found {len(exact_groups)} unique canonical ingredient names")

    # 3. Build family lookup from known variant/substitute maps
    family_lookup = build_family_lookup()

    # 4. Assign each ingredient to a family
    # Structure: family_name -> { family_type, members: [material_dicts] }
    families = defaultdict(lambda: {'family_type': None, 'members': []})

    assigned = set()
    for canonical_name, group_materials in exact_groups.items():
        if canonical_name in family_lookup:
            fam_name, fam_type = family_lookup[canonical_name]
            families[fam_name]['family_type'] = fam_type
            families[fam_name]['members'].extend(group_materials)
            assigned.add(canonical_name)
        else:
            # Standalone exact match — its own family
            families[canonical_name]['family_type'] = 'exact_match'
            families[canonical_name]['members'].extend(group_materials)
            assigned.add(canonical_name)

    print(f"Assigned to {len(families)} families")
    form_variants = sum(1 for f in families.values() if f['family_type'] == 'form_variant')
    func_subs = sum(1 for f in families.values() if f['family_type'] == 'functional_substitute')
    exact = sum(1 for f in families.values() if f['family_type'] == 'exact_match')
    print(f"  - exact_match: {exact}")
    print(f"  - form_variant: {form_variants}")
    print(f"  - functional_substitute: {func_subs}")

    # 5. Write to database
    create_tables()

    conn = get_connection()
    try:
        # Clear existing data
        conn.execute("DELETE FROM Ingredient_Family_Member")
        conn.execute("DELETE FROM Ingredient_Family")

        for family_name, family_data in families.items():
            # Get unique canonical names in this family
            canonical_names = set(m['canonical_name'] for m in family_data['members'])
            for cn in canonical_names:
                cursor = conn.execute(
                    "INSERT INTO Ingredient_Family (canonical_name, family_name, family_type) VALUES (?, ?, ?)",
                    (cn, family_name, family_data['family_type'])
                )
                family_id = cursor.lastrowid

                # Insert members for this canonical name
                for m in family_data['members']:
                    if m['canonical_name'] == cn:
                        conn.execute(
                            "INSERT OR IGNORE INTO Ingredient_Family_Member (family_id, product_id, canonical_name, company_id) VALUES (?, ?, ?, ?)",
                            (family_id, m['Id'], cn, m['CompanyId'])
                        )

        conn.commit()
        print("Saved to database.")

        # Stats
        count = conn.execute("SELECT COUNT(*) FROM Ingredient_Family").fetchone()[0]
        member_count = conn.execute("SELECT COUNT(*) FROM Ingredient_Family_Member").fetchone()[0]
        print(f"Total families in DB: {count}")
        print(f"Total family members in DB: {member_count}")

    finally:
        conn.close()

    return families


if __name__ == "__main__":
    resolve_all()

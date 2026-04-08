"""
Functional Role Labeling:
- Define role taxonomy for CPG supplement ingredients
- Heuristic pass: map ~70% by name pattern
- Store results in Ingredient_Role table
- LLM pass for ambiguous cases can be added later (Phase 2)
"""
import re
from typing import Dict, List, Tuple, Optional

from db import get_connection, query, execute_script
from ingredients import parse_ingredient_name

# ---------------------------------------------------------------------------
# Role taxonomy
# ---------------------------------------------------------------------------

ROLES = [
    'active_ingredient',     # Main therapeutic/nutritional component (catch-all active)
    'protein_source',        # Primary protein (whey, pea, collagen)
    'vitamin_mineral',       # Vitamins and minerals (active)
    'electrolyte_salt',      # Sodium, potassium, magnesium salts (in electrolyte products)
    'sweetener',             # Stevia, sucralose, acesulfame-K, sugar
    'emulsifier',            # Lecithin (soy/sunflower), polysorbate
    'filler_binder',         # Cellulose, starch, maltodextrin
    'lubricant',             # Magnesium stearate, stearic acid
    'capsule_shell',         # Gelatin, hypromellose, vegetable cellulose
    'coating',               # HPMC coating, shellac, glaze
    'disintegrant',          # Croscarmellose sodium
    'flavoring',             # Natural/artificial flavors
    'coloring',              # Titanium dioxide, FD&C dyes, beet extract
    'preservative',          # BHT, sorbic acid, tocopherols
    'carrier_oil',           # Soybean oil, sunflower oil, MCT oil
    'acid_buffer',           # Citric acid, malic acid
    'anti_caking',           # Silicon dioxide, silica
    'thickener_stabilizer',  # Xanthan gum, gellan gum, carrageenan
    'prebiotic_fiber',       # Inulin, FOS, polydextrose
    'other',
]

# ---------------------------------------------------------------------------
# Heuristic rules: pattern -> role
# Each rule is (regex_pattern, role). First match wins.
# ---------------------------------------------------------------------------

HEURISTIC_RULES: List[Tuple[str, str]] = [
    # === Protein sources ===
    (r'whey-protein', 'protein_source'),
    (r'pea-protein', 'protein_source'),
    (r'rice-protein', 'protein_source'),
    (r'brown-rice-protein', 'protein_source'),
    (r'hemp-seed-protein', 'protein_source'),
    (r'pumpkin-seed-protein', 'protein_source'),
    (r'collagen-peptides', 'protein_source'),
    (r'milk-protein', 'protein_source'),
    (r'bcaas', 'protein_source'),
    (r'l-leucine', 'protein_source'),
    (r'l-isoleucine', 'protein_source'),
    (r'l-valine', 'protein_source'),
    (r'^leucine$', 'protein_source'),

    # === Vitamins & Minerals (active) ===
    (r'^vitamin-', 'vitamin_mineral'),
    (r'^biotin$', 'vitamin_mineral'),
    (r'^folic-acid$', 'vitamin_mineral'),
    (r'^folate$', 'vitamin_mineral'),
    (r'^niacin$', 'vitamin_mineral'),
    (r'^niacinamide', 'vitamin_mineral'),
    (r'^nicotinamide$', 'vitamin_mineral'),
    (r'^thiamin', 'vitamin_mineral'),
    (r'^riboflavin', 'vitamin_mineral'),
    (r'^pyridoxine', 'vitamin_mineral'),
    (r'^cyanocobalamin', 'vitamin_mineral'),
    (r'^cholecalciferol', 'vitamin_mineral'),
    (r'^phytonadione$', 'vitamin_mineral'),
    (r'^pantothenic-acid$', 'vitamin_mineral'),
    (r'^d-calcium-pantothenate$', 'vitamin_mineral'),
    (r'^calcium-d-pantothenate$', 'vitamin_mineral'),
    (r'^calcium-pantothenate', 'vitamin_mineral'),
    (r'^d-alpha-tocopheryl', 'vitamin_mineral'),
    (r'^dl-alpha-tocopheryl', 'vitamin_mineral'),
    (r'^dl-alpha-tocopherol', 'vitamin_mineral'),
    (r'^retinyl-', 'vitamin_mineral'),
    (r'^ascorbic-acid', 'vitamin_mineral'),
    (r'^sodium-ascorbate$', 'vitamin_mineral'),
    (r'^calcium-ascorbate$', 'vitamin_mineral'),
    (r'^ascorbyl-palmitate$', 'vitamin_mineral'),
    (r'^beta-carotene$', 'vitamin_mineral'),
    (r'^lutein$', 'vitamin_mineral'),
    (r'^lycopene$', 'vitamin_mineral'),
    (r'^zeaxanthin$', 'vitamin_mineral'),
    (r'^astaxanthin$', 'vitamin_mineral'),
    (r'^coenzyme-q10$', 'vitamin_mineral'),
    (r'^coq10$', 'vitamin_mineral'),
    (r'^b-vitamins$', 'vitamin_mineral'),
    (r'^choline-bitartrate$', 'vitamin_mineral'),
    (r'^inositol$', 'vitamin_mineral'),
    (r'^para-amino-benzoic-acid$', 'vitamin_mineral'),
    (r'^rutin$', 'vitamin_mineral'),
    (r'^resveratrol$', 'vitamin_mineral'),
    (r'^omega-3', 'vitamin_mineral'),
    (r'^iodine$', 'vitamin_mineral'),
    (r'^potassium-iodide$', 'vitamin_mineral'),
    (r'^kelp-extract$', 'vitamin_mineral'),
    (r'^selenium$', 'vitamin_mineral'),
    (r'^sodium-selenite$', 'vitamin_mineral'),
    (r'^sodium-molybdate$', 'vitamin_mineral'),
    (r'^molybdenum$', 'vitamin_mineral'),
    (r'^boron$', 'vitamin_mineral'),
    (r'^boron-', 'vitamin_mineral'),
    (r'^vanadium', 'vitamin_mineral'),
    (r'^copper$', 'vitamin_mineral'),
    (r'^copper-sulfate$', 'vitamin_mineral'),
    (r'^cupric-', 'vitamin_mineral'),
    (r'^iron$', 'vitamin_mineral'),
    (r'^iron-glycinate$', 'vitamin_mineral'),
    (r'^ferrous-fumarate$', 'vitamin_mineral'),
    (r'^manganese$', 'vitamin_mineral'),
    (r'^manganese-', 'vitamin_mineral'),
    (r'^chromium$', 'vitamin_mineral'),
    (r'^chromium-', 'vitamin_mineral'),
    (r'^zinc$', 'vitamin_mineral'),
    (r'^zinc-oxide$', 'vitamin_mineral'),
    (r'^zinc-citrate$', 'vitamin_mineral'),
    (r'^zinc-sulfate$', 'vitamin_mineral'),
    (r'^zinc-chelate$', 'vitamin_mineral'),
    (r'^zinc-zinc-bisglycinate$', 'vitamin_mineral'),
    (r'^taurine$', 'vitamin_mineral'),

    # === Magnesium active forms (not stearate which is lubricant) ===
    (r'^magnesium-oxide$', 'vitamin_mineral'),
    (r'^magnesium-citrate$', 'vitamin_mineral'),
    (r'^magnesium-glycinate$', 'vitamin_mineral'),
    (r'^magnesium-bisglycinate$', 'vitamin_mineral'),
    (r'^magnesium-malate$', 'vitamin_mineral'),
    (r'^magnesium-carbonate$', 'vitamin_mineral'),
    (r'^magnesium-taurate$', 'vitamin_mineral'),
    (r'^magnesium-taurinate$', 'vitamin_mineral'),
    (r'^magnesium-aspartate$', 'vitamin_mineral'),
    (r'^magnesium-l-threonate', 'vitamin_mineral'),
    (r'^magnesium-amino-acid-chelate$', 'vitamin_mineral'),
    (r'^magnesium-dimagnesium-malate$', 'vitamin_mineral'),
    (r'^magnesium$', 'vitamin_mineral'),
    (r'^aquamin-mg-soluble$', 'vitamin_mineral'),

    # === Calcium active forms (not stearate) ===
    (r'^calcium-carbonate$', 'vitamin_mineral'),
    (r'^calcium-citrate$', 'vitamin_mineral'),
    (r'^calcium-lactate-gluconate$', 'vitamin_mineral'),
    (r'^calcium$', 'vitamin_mineral'),
    (r'^tricalcium-phosphate$', 'vitamin_mineral'),
    (r'^dicalcium-phosphate$', 'vitamin_mineral'),
    (r'^dibasic-calcium-phosphate', 'vitamin_mineral'),

    # === Electrolyte salts ===
    (r'^potassium-chloride$', 'electrolyte_salt'),
    (r'^potassium-citrate$', 'electrolyte_salt'),
    (r'^potassium-gluconate$', 'electrolyte_salt'),
    (r'^potassium-phosphate$', 'electrolyte_salt'),
    (r'^potassium-aspartate$', 'electrolyte_salt'),
    (r'^dipotassium-phosphate$', 'electrolyte_salt'),
    (r'^potassium-alginate$', 'electrolyte_salt'),
    (r'^potassium$', 'electrolyte_salt'),
    (r'^sodium-chloride$', 'electrolyte_salt'),
    (r'^sodium-citrate$', 'electrolyte_salt'),
    (r'^sodium$', 'electrolyte_salt'),
    (r'^chloride$', 'electrolyte_salt'),
    (r'^salt$', 'electrolyte_salt'),
    (r'^salt-sodium-chloride$', 'electrolyte_salt'),
    (r'^sea-salt$', 'electrolyte_salt'),
    (r'^pink-himalayan-salt$', 'electrolyte_salt'),
    (r'^kalahari-desert-salt$', 'electrolyte_salt'),
    (r'^concentrace-trace-minerals$', 'electrolyte_salt'),
    (r'^trace-mineral-concentrate$', 'electrolyte_salt'),
    (r'^coconut-water', 'electrolyte_salt'),

    # === Sweeteners ===
    (r'^stevia', 'sweetener'),
    (r'^organic-stevia', 'sweetener'),
    (r'^rebaudioside', 'sweetener'),
    (r'^sucralose$', 'sweetener'),
    (r'^acesulfame-potassium$', 'sweetener'),
    (r'^stevia-or-sucralose', 'sweetener'),
    (r'^monk-fruit', 'sweetener'),
    (r'^organic-erythritol$', 'sweetener'),
    (r'^sugar$', 'sweetener'),
    (r'^sucrose$', 'sweetener'),
    (r'^cane-sugar$', 'sweetener'),
    (r'^pure-cane-sugar$', 'sweetener'),
    (r'^organic-cane-sugar$', 'sweetener'),
    (r'^coconut-sugar$', 'sweetener'),
    (r'^dextrose$', 'sweetener'),
    (r'^anhydrous-dextrose$', 'sweetener'),
    (r'^glucose$', 'sweetener'),
    (r'^tapioca-syrup$', 'sweetener'),
    (r'^sorbitol$', 'sweetener'),

    # === Emulsifiers ===
    (r'lecithin', 'emulsifier'),
    (r'^polysorbate', 'emulsifier'),

    # === Capsule shells ===
    (r'^gelatin-capsule', 'capsule_shell'),
    (r'^gelatin$', 'capsule_shell'),
    (r'^bone-gelatin', 'capsule_shell'),
    (r'^soft-gel-capsule', 'capsule_shell'),
    (r'^softgel', 'capsule_shell'),
    (r'^hypromellose', 'capsule_shell'),
    (r'^hydroxypropyl-methyl', 'capsule_shell'),
    (r'^hydroxypropylmethyl', 'capsule_shell'),
    (r'^vegan-capsule', 'capsule_shell'),
    (r'^vegetarian-capsule$', 'capsule_shell'),
    (r'^plantgel-capsule$', 'capsule_shell'),
    (r'^gummy-base$', 'capsule_shell'),

    # === Lubricants ===
    (r'^magnesium-stearate$', 'lubricant'),
    (r'^vegetable-magnesium-stearate$', 'lubricant'),
    (r'^stearic-acid$', 'lubricant'),
    (r'^vegetable-stearic-acid$', 'lubricant'),
    (r'^magnesium-silicate$', 'lubricant'),

    # === Filler / binder ===
    (r'^microcrystalline-cellulose$', 'filler_binder'),
    (r'^cellulose-gel$', 'filler_binder'),
    (r'^cellulose-gum$', 'filler_binder'),
    (r'^cellulose$', 'filler_binder'),
    (r'^vegetable-cellulose$', 'filler_binder'),
    (r'^modified-cellulose$', 'filler_binder'),
    (r'^carboxymethylcellulose', 'filler_binder'),
    (r'^maltodextrin$', 'filler_binder'),
    (r'^organic-maltodextrin$', 'filler_binder'),
    (r'^modified-food-starch$', 'filler_binder'),
    (r'^starch$', 'filler_binder'),
    (r'^pea-starch$', 'filler_binder'),
    (r'^rice-flour$', 'filler_binder'),
    (r'^rice-powder$', 'filler_binder'),
    (r'^polydextrose$', 'filler_binder'),

    # === Coating ===
    (r'^aqueous-coating$', 'coating'),
    (r'^organic-coating$', 'coating'),
    (r'^pharmaceutical-glaze$', 'coating'),
    (r'^lac-resin$', 'coating'),
    (r'^non-gmo-corn-zein$', 'coating'),
    (r'^polyvinyl-alcohol$', 'coating'),
    (r'^polyethylene-glycol$', 'coating'),
    (r'^carnauba-wax$', 'coating'),

    # === Disintegrants ===
    (r'^croscarmellose-sodium$', 'disintegrant'),
    (r'^sodium-starch-glycolate$', 'disintegrant'),
    (r'^polyvinylpolypyrrolidone$', 'disintegrant'),

    # === Flavoring ===
    (r'flavor', 'flavoring'),
    (r'^cocoa$', 'flavoring'),
    (r'^cocoa-powder', 'flavoring'),
    (r'^cocoa-processed', 'flavoring'),
    (r'^cinnamon$', 'flavoring'),
    (r'^ground-vanilla', 'flavoring'),
    (r'^organic-vanilla', 'flavoring'),
    (r'^lemon-juice-powder$', 'flavoring'),

    # === Coloring ===
    (r'^titanium-dioxide$', 'coloring'),
    (r'blue-.*lake', 'coloring'),
    (r'red-.*lake', 'coloring'),
    (r'yellow-.*lake', 'coloring'),
    (r'^fd-and-c-', 'coloring'),
    (r'^beet-extract$', 'coloring'),
    (r'^beet-juice-powder$', 'coloring'),
    (r'^beet-powder$', 'coloring'),
    (r'^coloring-concentrates$', 'coloring'),
    (r'^fruit-and-vegetable-juice$', 'coloring'),

    # === Preservatives ===
    (r'^bht$', 'preservative'),
    (r'^sorbic-acid$', 'preservative'),
    (r'^sodium-benzoate$', 'preservative'),
    (r'^tocopherols$', 'preservative'),
    (r'^organic-rosemary-extract$', 'preservative'),
    (r'^organic-rice-bran-extract$', 'preservative'),

    # === Carrier oils ===
    (r'^soybean-oil$', 'carrier_oil'),
    (r'^sunflower-oil$', 'carrier_oil'),
    (r'^safflower-oil$', 'carrier_oil'),
    (r'^coconut-mct-oil$', 'carrier_oil'),
    (r'^medium-chain-triglycerides', 'carrier_oil'),
    (r'^olive-oil$', 'carrier_oil'),
    (r'^palm-oil$', 'carrier_oil'),
    (r'^corn-oil$', 'carrier_oil'),
    (r'^oil-fill$', 'carrier_oil'),

    # === Acid buffers ===
    (r'^citric-acid$', 'acid_buffer'),
    (r'^non-gmo-citric-acid$', 'acid_buffer'),
    (r'^malic-acid$', 'acid_buffer'),
    (r'^dl-tartaric-acid$', 'acid_buffer'),
    (r'^lactic-acid$', 'acid_buffer'),

    # === Anti-caking ===
    (r'^silicon-dioxide$', 'anti_caking'),
    (r'^silica$', 'anti_caking'),
    (r'^sodium-aluminum-silicate$', 'anti_caking'),
    (r'^talc$', 'anti_caking'),

    # === Thickener / stabilizer ===
    (r'^xanthan-gum$', 'thickener_stabilizer'),
    (r'^gellan-gum$', 'thickener_stabilizer'),
    (r'^gum-arabic$', 'thickener_stabilizer'),
    (r'^gum-acacia$', 'thickener_stabilizer'),
    (r'^organic-gum-acacia$', 'thickener_stabilizer'),
    (r'^acacia-gum$', 'thickener_stabilizer'),
    (r'^organic-acacia$', 'thickener_stabilizer'),
    (r'^carrageenan$', 'thickener_stabilizer'),

    # === Prebiotic fiber ===
    (r'^inulin$', 'prebiotic_fiber'),
    (r'^organic-inulin$', 'prebiotic_fiber'),
    (r'^organic-agave-inulin', 'prebiotic_fiber'),
    (r'^blue-agave-inulin$', 'prebiotic_fiber'),
    (r'^fructooligosaccharides$', 'prebiotic_fiber'),
    (r'^organic-tapioca-fiber', 'prebiotic_fiber'),
    (r'^prebiotic-fiber$', 'prebiotic_fiber'),

    # === Active ingredients (specialty) ===
    (r'^grape-seed-extract$', 'active_ingredient'),
    (r'^green-tea-extract$', 'active_ingredient'),
    (r'^rhodiola-rosea', 'active_ingredient'),
    (r'^pomegranate-extract$', 'active_ingredient'),
    (r'^organic-pomegranate', 'active_ingredient'),
    (r'^organic-turmeric$', 'active_ingredient'),
    (r'^organic-ginger$', 'active_ingredient'),
    (r'^black-pepper-concentrate$', 'active_ingredient'),
    (r'^alfalfa-leaf$', 'active_ingredient'),
    (r'^citrus-bioflavonoids$', 'active_ingredient'),
    (r'^lemon-bioflavonoid', 'active_ingredient'),
    (r'^hesperidin-complex$', 'active_ingredient'),
    (r'^epicor-postbiotic$', 'active_ingredient'),
    (r'^probiotic-cultures$', 'active_ingredient'),
    (r'^bifidobacterium', 'active_ingredient'),
    (r'^digestive-enzymes$', 'active_ingredient'),
    (r'^lactase$', 'active_ingredient'),
    (r'^rice-bran$', 'active_ingredient'),

    # === Catch-all blends ===
    (r'^energy-support', 'active_ingredient'),
    (r'^performance-support', 'active_ingredient'),
    (r'^fruit-nutrients$', 'active_ingredient'),
    (r'^vegetable-nutrients$', 'active_ingredient'),
    (r'^organic-food-complex', 'active_ingredient'),
    (r'^cultured-nutrients$', 'active_ingredient'),
    (r'^ferment-media$', 'active_ingredient'),
    (r'^effervescent-base$', 'filler_binder'),
    (r'^vegetable-acetoglycerides$', 'emulsifier'),

    # === Miscellaneous ===
    (r'^glycerin$', 'carrier_oil'),
    (r'^vegetable-glycerin$', 'carrier_oil'),
    (r'^sulfate$', 'electrolyte_salt'),
    (r'^blend-of-oils', 'carrier_oil'),
    (r'^natural-vanilla$', 'flavoring'),
    (r'^organic-rice-dextrins$', 'filler_binder'),
    (r'^sodium-alginate$', 'thickener_stabilizer'),
]


# ---------------------------------------------------------------------------
# Heuristic labeling engine
# ---------------------------------------------------------------------------

def label_ingredient(canonical_name: str) -> Tuple[str, float]:
    """
    Label a single ingredient with its functional role.
    Returns (role, confidence).
    """
    for pattern, role in HEURISTIC_RULES:
        if re.search(pattern, canonical_name):
            return (role, 0.9)

    # No match
    return ('other', 0.3)


# ---------------------------------------------------------------------------
# Table creation and main pipeline
# ---------------------------------------------------------------------------

def create_tables():
    execute_script("""
        CREATE TABLE IF NOT EXISTS Ingredient_Role (
            product_id INTEGER NOT NULL,
            ingredient_id INTEGER NOT NULL,
            canonical_name TEXT NOT NULL,
            functional_role TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0.5,
            method TEXT NOT NULL DEFAULT 'heuristic',
            PRIMARY KEY (product_id, ingredient_id),
            FOREIGN KEY (product_id) REFERENCES Product(Id),
            FOREIGN KEY (ingredient_id) REFERENCES Product(Id)
        );
    """)


def label_all():
    """Run functional role labeling for all BOM components."""
    print("=== Functional Role Labeling ===")

    # Get all BOM components with their canonical names
    rows = query("""
        SELECT b.ProducedProductId as product_id,
               bc.ConsumedProductId as ingredient_id,
               p_rm.SKU as ingredient_sku
        FROM BOM_Component bc
        JOIN BOM b ON bc.BOMId = b.Id
        JOIN Product p_rm ON bc.ConsumedProductId = p_rm.Id
        WHERE p_rm.Type = 'raw-material'
    """)
    print(f"Total BOM components to label: {len(rows)}")

    # Label each one
    results = []
    role_counts = {}
    unmatched = []

    for row in rows:
        canonical_name = parse_ingredient_name(row['ingredient_sku'])
        role, confidence = label_ingredient(canonical_name)
        results.append((
            row['product_id'],
            row['ingredient_id'],
            canonical_name,
            role,
            confidence,
            'heuristic',
        ))
        role_counts[role] = role_counts.get(role, 0) + 1
        if role == 'other':
            unmatched.append(canonical_name)

    # Stats
    print(f"\nRole distribution:")
    for role, count in sorted(role_counts.items(), key=lambda x: -x[1]):
        pct = count / len(results) * 100
        print(f"  {role:25s}: {count:4d} ({pct:.1f}%)")

    matched = len(results) - role_counts.get('other', 0)
    print(f"\nMatched: {matched}/{len(results)} ({matched/len(results)*100:.1f}%)")

    if unmatched:
        unique_unmatched = sorted(set(unmatched))
        print(f"Unmatched unique ingredients ({len(unique_unmatched)}):")
        for name in unique_unmatched[:20]:
            print(f"  - {name}")
        if len(unique_unmatched) > 20:
            print(f"  ... and {len(unique_unmatched) - 20} more")

    # Write to database
    create_tables()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM Ingredient_Role")
        conn.executemany(
            """INSERT INTO Ingredient_Role
               (product_id, ingredient_id, canonical_name, functional_role, confidence, method)
               VALUES (?, ?, ?, ?, ?, ?)""",
            results
        )
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM Ingredient_Role").fetchone()[0]
        print(f"\nSaved {count} role labels to database.")
    finally:
        conn.close()

    return results


if __name__ == "__main__":
    label_all()

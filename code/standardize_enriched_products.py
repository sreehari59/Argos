import argparse
import json
import re
from pathlib import Path


DEFAULT_INPUT = Path(__file__).resolve().parent / "scraper" / "output" / "enriched_products.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "scraper" / "output" / "standardized_products.json"


# ---------------------------------------------------------------------------
# Task 1: Expanded product categories
# ---------------------------------------------------------------------------

PRODUCT_CATEGORIES = {
    # Proteins
    'whey_protein': [
        'whey protein', 'whey isolate', 'whey concentrate', 'gold standard whey',
        '100% whey', 'whey powder'
    ],
    'plant_protein': [
        'plant protein', 'plant-based protein', 'vegan protein', 'pea protein',
        'rice protein', 'hemp protein', 'soy protein'
    ],
    'collagen': [
        'collagen', 'collagen peptides', 'collagen powder', 'marine collagen'
    ],
    'casein': [
        'casein', 'micellar casein', 'slow release protein'
    ],

    # Sports Nutrition
    'creatine': [
        'creatine', 'creatine monohydrate', 'creatine hcl'
    ],
    'bcaa': [
        'bcaa', 'branched chain amino', 'amino acid'
    ],
    'pre_workout': [
        'pre-workout', 'pre workout', 'preworkout'
    ],
    'post_workout': [
        'post-workout', 'post workout', 'recovery'
    ],
    'electrolyte_drink_mix': [
        'electrolyte', 'hydration', 'liquid iv', 'pedialyte', 'lmnt',
        'nuun', 'drip drop', 'ultima'
    ],

    # Vitamins - Single
    'vitamin_d3': [
        'vitamin d3', 'vitamin d-3', 'd3 ', 'cholecalciferol', 'd3,',
        'vitamin d 3'
    ],
    'vitamin_d2': [
        'vitamin d2', 'ergocalciferol'
    ],
    'vitamin_c': [
        'vitamin c', 'ascorbic acid', 'ester-c'
    ],
    'vitamin_b12': [
        'vitamin b12', 'vitamin b-12', 'b12 ', 'methylcobalamin', 'cyanocobalamin'
    ],
    'vitamin_b_complex': [
        'b-complex', 'b complex', 'vitamin b complex', 'super b'
    ],
    'vitamin_a': [
        'vitamin a', 'retinol', 'beta carotene'
    ],
    'vitamin_e': [
        'vitamin e', 'tocopherol'
    ],
    'vitamin_k': [
        'vitamin k', 'vitamin k2', 'mk-7'
    ],
    'biotin': [
        'biotin', 'vitamin b7', 'hair skin nail'
    ],
    'folic_acid': [
        'folic acid', 'folate', 'methylfolate'
    ],

    # Minerals - Single
    'magnesium_glycinate': [
        'magnesium glycinate', 'magnesium bisglycinate'
    ],
    'magnesium_citrate': [
        'magnesium citrate'
    ],
    'magnesium_oxide': [
        'magnesium oxide'
    ],
    'magnesium_l_threonate': [
        'magnesium l-threonate', 'magtein', 'magnesium threonate'
    ],
    'magnesium_complex': [
        'magnesium complex', 'triple magnesium'
    ],
    'magnesium': [
        'magnesium'
    ],
    'calcium': [
        'calcium', 'calcium citrate', 'calcium carbonate'
    ],
    'zinc': [
        'zinc', 'zinc picolinate', 'zinc gluconate'
    ],
    'iron': [
        'iron', 'ferrous', 'ferritin', 'gentle iron'
    ],
    'potassium': [
        'potassium', 'potassium citrate', 'potassium gluconate'
    ],
    'selenium': [
        'selenium'
    ],

    # Multi-vitamins
    'multivitamin': [
        'multivitamin', 'multi-vitamin', 'multimineral', 'one daily',
        'once daily', 'complete vitamin', 'centrum', 'one a day'
    ],
    'prenatal': [
        'prenatal', 'pregnancy', 'postnatal', 'nursing'
    ],
    'mens_multi': [
        "men's multi", "men's one", 'one for men', 'multi for men'
    ],
    'womens_multi': [
        "women's multi", "women's one", 'one for women', 'multi for women'
    ],

    # Omega / Fish Oil
    'omega_3_fish_oil': [
        'omega-3', 'omega 3', 'fish oil', 'krill oil', 'cod liver',
        'epa', 'dha', 'algae oil'
    ],

    # Probiotics & Digestive
    'probiotic': [
        'probiotic', 'lactobacillus', 'bifidobacterium', 'cfu',
        'acidophilus', 'gut health'
    ],
    'prebiotic': [
        'prebiotic', 'inulin', 'fiber supplement'
    ],
    'digestive_enzyme': [
        'digestive enzyme', 'enzyme blend', 'bromelain', 'papain'
    ],

    # Sleep & Stress
    'melatonin': [
        'melatonin', 'sleep aid', 'sleep support'
    ],
    'ashwagandha': [
        'ashwagandha', 'ksm-66', 'sensoril', 'withania'
    ],
    'magnesium_sleep': [
        'calm', 'relaxation', 'stress relief'
    ],

    # Herbs & Botanicals
    'turmeric_curcumin': [
        'turmeric', 'curcumin', 'curcuminoid'
    ],
    'elderberry': [
        'elderberry', 'sambucus'
    ],
    'echinacea': [
        'echinacea'
    ],
    'ginger': [
        'ginger root', 'ginger extract'
    ],
    'garlic': [
        'garlic', 'allicin', 'aged garlic'
    ],

    # Joint & Bone
    'glucosamine_chondroitin': [
        'glucosamine', 'chondroitin', 'joint support', 'joint health'
    ],
    'coq10': [
        'coq10', 'coenzyme q10', 'ubiquinol', 'ubiquinone'
    ],

    # Special categories
    'greens_powder': [
        'greens powder', 'super greens', 'green superfood', 'spirulina',
        'chlorella', 'wheatgrass'
    ],
    'fiber': [
        'fiber supplement', 'psyllium', 'metamucil', 'benefiber'
    ],
}

# Check specific before generic
CATEGORY_PRIORITY = [
    # Specific magnesium forms before generic "magnesium"
    'magnesium_glycinate', 'magnesium_citrate', 'magnesium_oxide',
    'magnesium_l_threonate', 'magnesium_complex',
    # Specific multis before generic
    'prenatal', 'mens_multi', 'womens_multi',
    # Everything else
    'whey_protein', 'plant_protein', 'collagen', 'casein',
    'creatine', 'bcaa', 'pre_workout', 'post_workout', 'electrolyte_drink_mix',
    'vitamin_d3', 'vitamin_d2', 'vitamin_c', 'vitamin_b12', 'vitamin_b_complex',
    'vitamin_a', 'vitamin_e', 'vitamin_k', 'biotin', 'folic_acid',
    'calcium', 'zinc', 'iron', 'potassium', 'selenium',
    'omega_3_fish_oil', 'probiotic', 'prebiotic', 'digestive_enzyme',
    'melatonin', 'ashwagandha', 'turmeric_curcumin', 'elderberry',
    'echinacea', 'ginger', 'garlic',
    'glucosamine_chondroitin', 'coq10', 'greens_powder', 'fiber',
    # Generic fallbacks LAST
    'magnesium', 'multivitamin',
]


# ---------------------------------------------------------------------------
# Task 2: Dosage form extraction
# ---------------------------------------------------------------------------

DOSAGE_FORMS = {
    'softgels': ['softgel', 'soft gel', 'soft-gel'],
    'capsules': ['capsule', 'vcap', 'veggie cap', 'vegetable capsule'],
    'tablets': ['tablet', 'caplet', 'tab '],
    'gummies': ['gummy', 'gummies', 'gummi'],
    'powder': ['powder', 'pwdr'],
    'liquid': ['liquid', 'drops', 'tincture', 'syrup'],
    'chewables': ['chewable', 'chew '],
    'lozenges': ['lozenge'],
    'packets': ['packet', 'stick pack', 'sachet', 'single serve'],
    'spray': ['spray', 'mist'],
}


def extract_dosage_form(product_name: str, ingredients_raw: str = None) -> str | None:
    """
    Extract dosage form from product name or ingredients.

    Priority:
    1. Explicit form in product name
    2. Infer from ingredients (e.g., "gelatin capsule")
    """
    if not product_name:
        return None

    name_lower = product_name.lower()

    for form, patterns in DOSAGE_FORMS.items():
        for pattern in patterns:
            if pattern in name_lower:
                return form

    if ingredients_raw:
        ing_lower = ingredients_raw.lower()
        for form, patterns in DOSAGE_FORMS.items():
            for pattern in patterns:
                if pattern in ing_lower:
                    return form

    return None


# ---------------------------------------------------------------------------
# Task 3: Ingredient signals extraction
# ---------------------------------------------------------------------------

INGREDIENT_SIGNALS = {
    # Proteins
    'whey_protein': ['whey protein', 'whey isolate', 'whey concentrate'],
    'casein': ['casein', 'micellar casein'],
    'pea_protein': ['pea protein'],
    'rice_protein': ['rice protein'],
    'soy_protein': ['soy protein', 'soy isolate'],
    'collagen': ['collagen', 'hydrolyzed collagen'],

    # Vitamins
    'vitamin_d3': ['cholecalciferol', 'vitamin d3'],
    'vitamin_d2': ['ergocalciferol'],
    'vitamin_c': ['ascorbic acid', 'sodium ascorbate', 'vitamin c'],
    'vitamin_e': ['tocopherol', 'd-alpha tocopherol'],
    'vitamin_a': ['retinyl', 'retinol', 'beta-carotene', 'beta carotene'],
    'vitamin_k2': ['menaquinone', 'mk-7', 'vitamin k2'],
    'vitamin_b1': ['thiamine', 'thiamin'],
    'vitamin_b2': ['riboflavin'],
    'vitamin_b3': ['niacin', 'niacinamide', 'nicotinic acid'],
    'vitamin_b5': ['pantothenic', 'd-calcium pantothenate'],
    'vitamin_b6': ['pyridoxine', 'pyridoxal'],
    'vitamin_b7': ['biotin'],
    'vitamin_b9': ['folic acid', 'folate', 'methylfolate'],
    'vitamin_b12': ['cyanocobalamin', 'methylcobalamin', 'cobalamin'],

    # Minerals
    'magnesium_glycinate': ['magnesium glycinate', 'magnesium bisglycinate'],
    'magnesium_citrate': ['magnesium citrate'],
    'magnesium_oxide': ['magnesium oxide'],
    'magnesium': ['magnesium'],
    'calcium': ['calcium carbonate', 'calcium citrate', 'calcium '],
    'zinc': ['zinc oxide', 'zinc gluconate', 'zinc picolinate', 'zinc '],
    'iron': ['ferrous', 'iron ', 'ferric'],
    'potassium': ['potassium citrate', 'potassium chloride', 'potassium '],
    'sodium': ['sodium chloride', 'sodium citrate', 'sodium '],
    'selenium': ['selenium', 'selenomethionine'],
    'chromium': ['chromium picolinate', 'chromium '],
    'iodine': ['potassium iodide', 'iodine'],

    # Amino Acids
    'bcaa': ['leucine', 'isoleucine', 'valine'],
    'glutamine': ['l-glutamine', 'glutamine'],
    'creatine': ['creatine monohydrate', 'creatine hcl', 'creatine '],
    'taurine': ['taurine'],
    'glycine': ['glycine'],

    # Herbs & Botanicals
    'ashwagandha': ['ashwagandha', 'withania somnifera'],
    'turmeric': ['turmeric', 'curcumin', 'curcuma longa'],
    'ginger': ['ginger', 'zingiber'],
    'garlic': ['garlic', 'allium sativum', 'allicin'],
    'elderberry': ['elderberry', 'sambucus'],
    'echinacea': ['echinacea'],
    'ginseng': ['ginseng', 'panax'],
    'green_tea': ['green tea extract', 'egcg', 'camellia sinensis'],

    # Other
    'probiotics': ['lactobacillus', 'bifidobacterium', 'probiotic blend'],
    'omega_3': ['fish oil', 'epa', 'dha', 'omega-3'],
    'coq10': ['coenzyme q10', 'ubiquinol', 'ubiquinone'],
    'glucosamine': ['glucosamine'],
    'chondroitin': ['chondroitin'],
    'melatonin': ['melatonin'],

    # Sweeteners & Fillers
    'stevia': ['stevia', 'steviol'],
    'sucralose': ['sucralose'],
    'sugar_alcohol': ['erythritol', 'xylitol', 'sorbitol', 'maltitol'],
    'maltodextrin': ['maltodextrin'],
    'gelatin': ['gelatin', 'bovine gelatin', 'porcine gelatin'],
    'cellulose': ['microcrystalline cellulose', 'cellulose'],
    'magnesium_stearate': ['magnesium stearate'],
    'silicon_dioxide': ['silicon dioxide', 'silica'],
}

# Check specific forms before their generic parent
_INGREDIENT_PRIORITY = [
    'magnesium_glycinate', 'magnesium_citrate', 'magnesium_oxide',
    'vitamin_d3', 'vitamin_d2',
]


def extract_ingredient_signals(ingredients_raw: str) -> list[str]:
    """
    Extract standardized ingredient signals from raw ingredient text.
    """
    if not ingredients_raw:
        return []

    ing_lower = ingredients_raw.lower()
    signals: list[str] = []
    checked: set[str] = set()

    # First pass: priority ingredients
    for signal in _INGREDIENT_PRIORITY:
        if signal in INGREDIENT_SIGNALS:
            if any(p in ing_lower for p in INGREDIENT_SIGNALS[signal]):
                signals.append(signal)
                checked.add(signal)
                # If a specific magnesium form matched, skip generic magnesium
                if signal.startswith('magnesium_'):
                    checked.add('magnesium')

    # Second pass: everything else
    for signal, patterns in INGREDIENT_SIGNALS.items():
        if signal not in checked:
            if any(p in ing_lower for p in patterns):
                signals.append(signal)

    return list(set(signals))


# ---------------------------------------------------------------------------
# Task 4: Target demographic extraction
# ---------------------------------------------------------------------------

def extract_target_demographic(product_name: str) -> str:
    """
    Extract target demographic from product name.
    """
    if not product_name:
        return 'unisex'

    name_lower = product_name.lower()

    if any(kw in name_lower for kw in ['prenatal', 'pregnancy', 'pregnant', 'postnatal', 'nursing']):
        return 'prenatal'

    if any(kw in name_lower for kw in ['kid', 'child', 'children', "kids'", "children's"]):
        return 'children'

    if any(kw in name_lower for kw in ['teen', 'adolescent', "teen's"]):
        return 'teens'

    if any(kw in name_lower for kw in ['50+', '50 plus', 'senior', '55+', '65+', 'adults 50', 'over 50']):
        return 'adults_50_plus'

    if any(kw in name_lower for kw in ["women's", 'for women', 'woman ', 'female', 'her ', 'ladies']):
        return 'women'

    if any(kw in name_lower for kw in ["men's", 'for men', 'man ', 'male', 'his ', 'gentleman']):
        return 'men'

    return 'unisex'


# ---------------------------------------------------------------------------
# Task 5: Certification filtering
# ---------------------------------------------------------------------------

VALID_CERTIFICATIONS = {
    'usda_organic': ['usda organic', 'certified organic', 'organic certified'],
    'non_gmo_project': ['non-gmo project', 'non gmo project', 'nongmo project verified'],
    'nsf_certified': ['nsf certified', 'nsf sport', 'nsf international', 'nsf contents'],
    'nsf_sport': ['nsf certified for sport', 'nsf sport'],
    'usp_verified': ['usp verified', 'usp dietary supplement verified'],
    'informed_sport': ['informed sport', 'informed-sport'],
    'informed_choice': ['informed choice', 'informed-choice'],
    'gmp_certified': ['gmp certified', 'cgmp', 'good manufacturing practice'],
    'kosher': ['kosher', 'ou kosher', 'ok kosher', 'star-k'],
    'halal': ['halal', 'halal certified'],
    'vegan_certified': ['certified vegan', 'vegan society', 'vegan.org'],
    'vegetarian_certified': ['vegetarian society'],
    'gluten_free_certified': ['certified gluten-free', 'gfco', 'gluten-free certification'],
    'non_gmo': ['non-gmo', 'non gmo', 'no gmo'],
    'third_party_tested': ['third party tested', '3rd party tested', 'independently tested'],
}

CERTIFICATION_GARBAGE = [
    'star', 'rating', 'review', 'best seller', 'choice', 'amazon',
    '%', 'save', 'off', 'sale', 'deal', 'price', 'shipping',
    'subscribe', 'autoship', 'favorite', 'new', 'improved',
    'out of', 'in stock', 'sold by', 'ships from',
]


def extract_certifications(raw_certifications: list[str]) -> list[str]:
    """
    Filter raw certifications to valid, standardized certification list.
    """
    if not raw_certifications:
        return []

    valid_certs: list[str] = []

    for raw_cert in raw_certifications:
        cert_lower = raw_cert.lower().strip()

        if any(garbage in cert_lower for garbage in CERTIFICATION_GARBAGE):
            continue

        if len(cert_lower) < 3 or len(cert_lower) > 100:
            continue

        for cert_key, patterns in VALID_CERTIFICATIONS.items():
            if any(pattern in cert_lower for pattern in patterns):
                valid_certs.append(cert_key)
                break

    return list(set(valid_certs))


# ---------------------------------------------------------------------------
# Task 6: Dietary flags extraction
# ---------------------------------------------------------------------------

DIETARY_FLAGS = {
    'gluten_free': ['gluten-free', 'gluten free', 'no gluten', 'without gluten'],
    'dairy_free': ['dairy-free', 'dairy free', 'no dairy', 'lactose-free', 'lactose free'],
    'soy_free': ['soy-free', 'soy free', 'no soy'],
    'nut_free': ['nut-free', 'nut free', 'no nuts', 'peanut-free', 'tree nut free'],
    'egg_free': ['egg-free', 'egg free', 'no eggs'],
    'vegan': ['vegan', 'plant-based', 'plant based', '100% vegan'],
    'vegetarian': ['vegetarian', 'veggie', 'lacto-ovo'],
    'organic': ['organic', 'usda organic', 'certified organic'],
    'non_gmo': ['non-gmo', 'non gmo', 'no gmo', 'gmo-free', 'gmo free'],
    'kosher': ['kosher'],
    'halal': ['halal'],
    'sugar_free': ['sugar-free', 'sugar free', 'no sugar', 'zero sugar', 'unsweetened'],
    'low_sodium': ['low sodium', 'low-sodium', 'no sodium', 'sodium free'],
    'keto': ['keto', 'keto-friendly', 'ketogenic'],
    'paleo': ['paleo', 'paleo-friendly'],
    'whole30': ['whole30', 'whole 30'],
    'caffeine_free': ['caffeine-free', 'caffeine free', 'no caffeine', 'decaf'],
    'artificial_free': ['no artificial', 'artificial-free', 'no synthetic'],
    'preservative_free': ['no preservatives', 'preservative-free'],
    'filler_free': ['no fillers', 'filler-free'],
    'allergen_free': ['allergen-free', 'hypoallergenic', 'free from common allergens'],
}


def extract_dietary_flags(
    raw_dietary_claims: list[str],
    product_name: str = None,
    ingredients_raw: str = None,
) -> list[str]:
    """
    Extract dietary flags from raw claims, product name, and ingredients.
    """
    flags: set[str] = set()

    all_text = ' '.join(raw_dietary_claims or []).lower()
    if product_name:
        all_text += ' ' + product_name.lower()

    for flag_key, patterns in DIETARY_FLAGS.items():
        if any(pattern in all_text for pattern in patterns):
            flags.add(flag_key)

    # Ingredient-based inference
    if ingredients_raw:
        ing_lower = ingredients_raw.lower()

        if 'gelatin' in ing_lower:
            flags.discard('vegan')
            flags.discard('vegetarian')

        if any(kw in ing_lower for kw in ['fish oil', 'fish gelatin', 'shellfish']):
            flags.discard('vegan')
            flags.discard('vegetarian')

    return list(flags)


# ---------------------------------------------------------------------------
# Task 1 (continued): Category extraction using priority-ordered substring match
# ---------------------------------------------------------------------------

def extract_product_category(product_name: str, ingredients_raw: str = None) -> str:
    """
    Determine product category from name and ingredients.
    Uses CATEGORY_PRIORITY to check specific categories before generic ones.
    """
    if not product_name:
        return 'unknown'

    combined = product_name.lower()
    if ingredients_raw:
        combined += ' ' + ingredients_raw.lower()

    for category in CATEGORY_PRIORITY:
        patterns = PRODUCT_CATEGORIES.get(category, [])
        if any(pattern in combined for pattern in patterns):
            return category

    return 'unknown'


# ---------------------------------------------------------------------------
# Retained helpers (brand, flavor, potency, allergen, etc.)
# ---------------------------------------------------------------------------

BRAND_RULES = [
    ("Optimum Nutrition", [r"\boptimum nutrition\b"]),
    ("Equate", [r"\bequate\b"]),
    ("Pedialyte", [r"\bpedialyte\b"]),
    ("Women's Best", [r"\bwomen'?s best\b"]),
    ("Liquid I.V.", [r"\bliquid i\.v\b"]),
    ("Spring Valley", [r"\bspring valley\b"]),
    ("Nature Made", [r"\bnature made\b"]),
    ("Premier Protein", [r"\bpremier protein\b"]),
    ("Ultima Replenisher", [r"\bultima replenisher\b", r"\bultima\b"]),
    ("Nordic Naturals", [r"\bnordic naturals\b"]),
    ("Centrum", [r"\bcentrum\b"]),
    ("Lifetime allOne", [r"\ballone\b"]),
    ("Electrolit", [r"\belectrolit\b"]),
    ("GreeNatr", [r"\bgreenatr\b"]),
    ("Greens First", [r"\bgreens first\b"]),
    ("AlkemyPower", [r"\balkemypower\b"]),
    ("TREVI", [r"\btrevi\b"]),
    ("Vitacost", [r"\bvitacost\b"]),
    ("PRIME Hydration", [r"\bprime hydration\b", r"\bprime hydration\+\b"]),
    ("Simply Tera's", [r"\bsimply tera'?s\b"]),
    ("PowderVitamin", [r"\bpowdervitamin\b"]),
    ("GMU Sport", [r"\bgmu sport\b"]),
    ("One A Day", [r"\bone a day\b"]),
    ("up&up", [r"\bup&up\b"]),
    ("LMNT", [r"\blmnt\b"]),
    ("21st Century", [r"\b21st century\b"]),
    ("GNC", [r"\bgnc\b"]),
]

FLAVOR_RULES = [
    "vanilla ice cream",
    "double rich chocolate",
    "chocolate peanut butter",
    "vanilla milkshake",
    "strawberry cream",
    "peanut butter cup",
    "sour cherry",
    "strawberry",
    "watermelon",
    "pineapple",
    "grape",
    "fruit punch",
    "apple",
    "lemon lime",
    "lemonade",
    "vanilla",
    "chocolate",
]

STORE_BRAND_BY_SOURCE = {
    "walmart": ["Equate", "Spring Valley"],
    "target": ["up&up"],
    "gnc": ["GNC"],
    "costco": ["Kirkland Signature"],
    "sams_club": ["Member's Mark"],
    "cvs": ["CVS Health"],
    "walgreens": ["Walgreens"],
    "vitacost": ["Vitacost"],
    "amazon": [],
}


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def infer_brand(record: dict, clean_name: str) -> str | None:
    scraped_brand = normalize_text(record.get("brand"))
    lower_name = clean_name.lower()

    for canonical_brand, patterns in BRAND_RULES:
        if any(re.search(pattern, lower_name) for pattern in patterns):
            return canonical_brand

    if scraped_brand:
        for canonical_brand, patterns in BRAND_RULES:
            if any(re.search(pattern, scraped_brand.lower()) for pattern in patterns):
                return canonical_brand
        if len(scraped_brand) >= 3:
            return scraped_brand

    source = record.get("source")
    fallback_store_brands = STORE_BRAND_BY_SOURCE.get(source, [])
    for store_brand in fallback_store_brands:
        if store_brand.lower() in lower_name:
            return store_brand

    return None


def infer_flavor(clean_name: str) -> str | None:
    lower_name = clean_name.lower()
    for flavor in FLAVOR_RULES:
        if flavor in lower_name:
            return flavor
    return None


def extract_potency(clean_name: str, ingredient_blob: str) -> list[str]:
    text = f"{clean_name} | {ingredient_blob}"
    matches = re.findall(r"\b\d+(?:\.\d+)?\s?(?:mg|mcg|iu|g)\b", text, flags=re.IGNORECASE)
    seen: list[str] = []
    for match in matches:
        value = match.upper().replace("MCG", "mcg").replace("MG", "mg")
        if value not in seen:
            seen.append(value)
    return seen


def extract_count(clean_name: str) -> str | None:
    match = re.search(r"\b(\d+)\s?(?:count|ct|servings?)\b", clean_name, flags=re.IGNORECASE)
    if match:
        return match.group(0)
    return None


def clean_allergen_contains(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        normalized = normalize_text(value)
        if not normalized:
            continue
        if len(normalized) > 80:
            continue
        if normalized.lower() in {"access denied"}:
            continue
        cleaned.append(normalized)
    return cleaned


# ---------------------------------------------------------------------------
# Task 7: Main standardization function
# ---------------------------------------------------------------------------

def standardize_record(record: dict) -> dict:
    clean_name = normalize_text(record.get("product_name"))
    ingredients_raw = normalize_text(record.get("ingredients_raw"))
    raw_dietary_claims = [normalize_text(v) for v in record.get("dietary_claims") or [] if normalize_text(v)]
    allergen_contains = clean_allergen_contains(record.get("allergen_contains") or [])
    allergen_free_from = [normalize_text(v) for v in record.get("allergen_free_from") or [] if normalize_text(v)]

    # Handle blocked/failed scrapes
    if clean_name == "Access Denied" or "access denied" in clean_name.lower():
        return {
            **record,
            "product_category": "blocked_page",
            "normalization_status": "blocked_page",
        }

    scrape_success = bool(record.get("scrape_success", True))
    if not scrape_success or not clean_name:
        return {
            **record,
            "product_category": "scrape_failed",
            "normalization_status": "scrape_failed",
        }

    product_category = extract_product_category(clean_name, ingredients_raw)
    dosage_form = extract_dosage_form(clean_name, ingredients_raw)
    target_demographic = extract_target_demographic(clean_name)
    dietary_flags = extract_dietary_flags(raw_dietary_claims, clean_name, ingredients_raw)
    certifications = extract_certifications(record.get("certifications") or [])
    ingredient_signals = extract_ingredient_signals(ingredients_raw)
    brand = infer_brand(record, clean_name)
    flavor = infer_flavor(clean_name)
    potency = extract_potency(clean_name, ingredients_raw)
    package_count = extract_count(clean_name)

    normalization_status = "needs_review" if product_category == "unknown" else "standardized"

    return {
        "sku": record.get("sku"),
        "source": record.get("source"),
        "retailer": record.get("source"),
        "url": record.get("url"),
        "scrape_success": record.get("scrape_success", False),
        "normalization_status": normalization_status,
        "product_name": clean_name or None,
        "product_category": product_category,
        "brand": brand,
        "dosage_form": dosage_form,
        "target_demographic": target_demographic,
        "flavor": flavor,
        "ingredient_signals": ingredient_signals,
        "dietary_flags": dietary_flags,
        "certifications": certifications,
        "allergen_contains": allergen_contains,
        "allergen_free_from": allergen_free_from,
        "potency": potency,
        "package_count_or_servings": package_count,
        "raw_product_name": record.get("product_name"),
        "raw_brand": record.get("brand"),
        "raw_dietary_claims": record.get("dietary_claims") or [],
        "raw_ingredients_raw": record.get("ingredients_raw"),
        "error_message": record.get("error_message"),
    }


# ---------------------------------------------------------------------------
# Task 8: Summary statistics
# ---------------------------------------------------------------------------

def summarize(records: list[dict]) -> dict:
    from collections import Counter

    summary: dict = {
        "record_count": len(records),
        "product_categories": dict(Counter(r.get("product_category") for r in records)),
        "dosage_forms": dict(Counter(r.get("dosage_form") for r in records if r.get("dosage_form"))),
        "target_demographics": dict(Counter(r.get("target_demographic") for r in records if r.get("target_demographic"))),
        "statuses": dict(Counter(r.get("normalization_status") for r in records)),
        "brands": dict(Counter(r.get("brand") for r in records)),
        "dietary_flags": dict(Counter(
            flag for r in records for flag in r.get("dietary_flags", [])
        )),
        "certifications": dict(Counter(
            cert for r in records for cert in r.get("certifications", [])
        )),
        "ingredient_signals": dict(Counter(
            sig for r in records for sig in r.get("ingredient_signals", [])
        )),
        "unknown_examples": [
            r.get("product_name", "")[:60]
            for r in records
            if r.get("product_category") == "unknown"
        ][:10],
    }

    # Sort each counter dict by count descending
    for key in ("product_categories", "dosage_forms", "target_demographics", "statuses",
                "brands", "dietary_flags", "certifications", "ingredient_signals"):
        summary[key] = dict(sorted(summary[key].items(), key=lambda item: (-item[1], item[0])))

    return summary


# ---------------------------------------------------------------------------
# Schema enumerations (for output metadata)
# ---------------------------------------------------------------------------

SCHEMA_PRODUCT_CATEGORIES = sorted(PRODUCT_CATEGORIES.keys()) + ["unknown", "blocked_page", "scrape_failed"]
SCHEMA_DOSAGE_FORMS = sorted(DOSAGE_FORMS.keys())
SCHEMA_TARGET_DEMOGRAPHICS = ["prenatal", "children", "teens", "adults_50_plus", "women", "men", "unisex"]
SCHEMA_DIETARY_FLAGS = sorted(DIETARY_FLAGS.keys())
SCHEMA_INGREDIENT_SIGNALS = sorted(INGREDIENT_SIGNALS.keys())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Rule-based standardization for enriched product records.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input enriched_products.json path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output standardized_products.json path")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    records = json.loads(input_path.read_text(encoding="utf-8"))
    standardized_records = [standardize_record(record) for record in records]
    payload = {
        "schema": {
            "product_categories": SCHEMA_PRODUCT_CATEGORIES,
            "dosage_forms": SCHEMA_DOSAGE_FORMS,
            "target_demographics": SCHEMA_TARGET_DEMOGRAPHICS,
            "dietary_flags": SCHEMA_DIETARY_FLAGS,
            "ingredient_signals": SCHEMA_INGREDIENT_SIGNALS,
        },
        "summary": summarize(standardized_records),
        "records": standardized_records,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(standardized_records)} standardized records to {output_path}")


if __name__ == "__main__":
    main()

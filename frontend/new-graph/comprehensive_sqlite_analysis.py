import sqlite3
import json
from collections import defaultdict, Counter
from datetime import datetime
from itertools import combinations

DB_PATH = 'db_filtered.sqlite'
OUTPUT_PATH = 'comprehensive_supply_chain.json'

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def to_lowercase_keys(d):
    """Convert dictionary keys to lowercase with proper formatting for JSON compatibility"""
    if isinstance(d, dict):
        result = {}
        for k, v in d.items():
            if isinstance(k, str):
                # Convert CompanyId -> company_id, ProductId -> product_id, etc.
                if k == 'CompanyId':
                    result['company_id'] = v
                elif k == 'ProductId':
                    result['product_id'] = v
                elif k == 'SupplierId':
                    result['supplier_id'] = v
                else:
                    result[k.lower()] = v
            else:
                result[k] = v
        return result
    return d

print("=" * 80)
print("COMPREHENSIVE SUPPLY CHAIN ANALYSIS - Filtered & Validated Dataset")
print("=" * 80)

conn = get_connection()
cursor = conn.cursor()

# ============================================================================
# 1. LOAD CORE ENTITIES
# ============================================================================
print("\n[1/12] Loading core entities...")

companies = cursor.execute("SELECT * FROM Company").fetchall()
products = cursor.execute("SELECT * FROM Product").fetchall()
boms = cursor.execute("SELECT * FROM BOM").fetchall()
bom_components = cursor.execute("SELECT * FROM BOM_Component").fetchall()
suppliers = cursor.execute("SELECT * FROM Supplier").fetchall()
supplier_products = cursor.execute("SELECT * FROM Supplier_Product").fetchall()

print(f"  ✓ Companies: {len(companies)}")
print(f"  ✓ Products: {len(products)}")
print(f"  ✓ BOMs: {len(boms)}")
print(f"  ✓ BOM Components: {len(bom_components)}")
print(f"  ✓ Suppliers: {len(suppliers)}")
print(f"  ✓ Supplier-Product links: {len(supplier_products)}")

# ============================================================================
# 2. LOAD ENRICHMENT DATA
# ============================================================================
print("\n[2/12] Loading enrichment data...")

enrichment_data = {}
enrichments = cursor.execute("SELECT * FROM Product_Enrichment").fetchall()
for row in enrichments:
    enrichment_data[row['ProductId']] = dict(row)
print(f"  ✓ Product enrichments: {len(enrichment_data)}")

standardization_data = {}
standardizations = cursor.execute("SELECT * FROM Product_Standardization").fetchall()
for row in standardizations:
    standardization_data[row['ProductId']] = dict(row)
print(f"  ✓ Product standardizations: {len(standardization_data)}")

# ============================================================================
# 3. LOAD PRICING DATA ⭐ NEW!
# ============================================================================
print("\n[3/12] Loading pricing data... ⭐")

pricing_data = {}
pricings = cursor.execute("SELECT * FROM Product_Pricing WHERE PriceUSD IS NOT NULL").fetchall()
for row in pricings:
    pricing_data[row['ProductId']] = dict(row)
print(f"  ✓ Products with pricing: {len(pricing_data)}")

if pricing_data:
    prices = [p['PriceUSD'] for p in pricing_data.values() if p['PriceUSD']]
    print(f"  ✓ Price range: ${min(prices):.2f} - ${max(prices):.2f}")
    print(f"  ✓ Average price: ${sum(prices)/len(prices):.2f}")

# ============================================================================
# 4. BUILD RELATIONSHIP MAPPINGS
# ============================================================================
print("\n[4/12] Building relationship mappings...")

# Product type classification
finished_goods = []
raw_materials = []
for product in products:
    p_dict = to_lowercase_keys(dict(product))
    if product['Type'] == 'finished-good':
        finished_goods.append(p_dict)
    else:
        raw_materials.append(p_dict)

print(f"  ✓ Finished Goods: {len(finished_goods)}")
print(f"  ✓ Raw Materials: {len(raw_materials)}")

# BOM mappings
bom_to_fg = {bom['Id']: bom['ProducedProductId'] for bom in boms}
fg_to_bom = {bom['ProducedProductId']: bom['Id'] for bom in boms}

# FG → RMs mapping
fg_to_rms = defaultdict(list)
for comp in bom_components:
    bom_id = comp['BOMId']
    if bom_id in bom_to_fg:
        fg_id = bom_to_fg[bom_id]
        rm_id = comp['ConsumedProductId']
        fg_to_rms[fg_id].append(rm_id)

# RM → FGs mapping
rm_to_fgs = defaultdict(list)
for fg_id, rms in fg_to_rms.items():
    for rm_id in rms:
        rm_to_fgs[rm_id].append(fg_id)

# Supplier → RMs mapping
supplier_to_rms = defaultdict(list)
for sp in supplier_products:
    supplier_to_rms[sp['SupplierId']].append(sp['ProductId'])

# RM → Suppliers mapping
rm_to_suppliers = defaultdict(list)
for sp in supplier_products:
    rm_to_suppliers[sp['ProductId']].append(sp['SupplierId'])

print(f"  ✓ FG-RM relationships: {len(fg_to_rms)}")
print(f"  ✓ RM-Supplier relationships: {len(rm_to_suppliers)}")

# ============================================================================
# 5. CRITICAL RAW MATERIALS ANALYSIS
# ============================================================================
print("\n[5/12] Analyzing critical raw materials...")

rm_usage_count = Counter()
for fg_id, rms in fg_to_rms.items():
    for rm_id in rms:
        rm_usage_count[rm_id] += 1

critical_raw_materials = rm_usage_count.most_common(100)
hub_materials = [rm for rm, count in critical_raw_materials if count >= 5]
print(f"  ✓ Hub materials (used in 5+ products): {len(hub_materials)}")

# ============================================================================
# 6. SINGLE-SOURCE RISK ANALYSIS
# ============================================================================
print("\n[6/12] Analyzing single-source risks...")

single_source_rms = []
multi_source_rms = []

for rm_id in rm_to_suppliers.keys():
    supplier_count = len(rm_to_suppliers[rm_id])
    if supplier_count == 1:
        single_source_rms.append(rm_id)
    else:
        multi_source_rms.append(rm_id)

print(f"  ✓ Single-source materials: {len(single_source_rms)}")
print(f"  ✓ Multi-source materials: {len(multi_source_rms)}")

# High-risk finished goods
high_risk_fgs = []
for fg_id, rms in fg_to_rms.items():
    if len(rms) == 0:
        continue
    single_source_count = sum(1 for rm_id in rms if rm_id in single_source_rms)
    risk_ratio = single_source_count / len(rms)
    
    fg = next((p for p in finished_goods if p['id'] == fg_id), None)
    if fg:
        high_risk_fgs.append({
            'fg_id': fg_id,
            'sku': fg['sku'],
            'company': fg['company_id'],
            'total_rms': len(rms),
            'single_source_rms': single_source_count,
            'risk_ratio': risk_ratio
        })

high_risk_fgs.sort(key=lambda x: x['risk_ratio'], reverse=True)
print(f"  ✓ High-risk products (>40% single-source): {len([fg for fg in high_risk_fgs if fg['risk_ratio'] >= 0.4])}")

# ============================================================================
# 7. PRODUCT SIMILARITY ANALYSIS
# ============================================================================
print("\n[7/12] Analyzing product similarity...")

product_similarity = []
fg_list = list(fg_to_rms.keys())

for i in range(len(fg_list)):
    for j in range(i + 1, len(fg_list)):
        fg_a, fg_b = fg_list[i], fg_list[j]
        rms_a = set(fg_to_rms[fg_a])
        rms_b = set(fg_to_rms[fg_b])
        
        shared = rms_a & rms_b
        if len(shared) >= 5:
            total = len(rms_a | rms_b)
            jaccard = len(shared) / total if total > 0 else 0
            product_similarity.append((fg_a, fg_b, len(shared), jaccard))

product_similarity.sort(key=lambda x: x[3], reverse=True)
print(f"  ✓ Similar product pairs (5+ shared materials): {len(product_similarity)}")

# ============================================================================
# 8. SUPPLIER REACH ANALYSIS
# ============================================================================
print("\n[8/12] Analyzing supplier reach...")

supplier_reach = {}
for supplier in suppliers:
    sid = supplier['Id']
    rms = supplier_to_rms.get(sid, [])
    
    # Find all FGs using these RMs
    affected_fgs = set()
    for rm_id in rms:
        affected_fgs.update(rm_to_fgs.get(rm_id, []))
    
    # Find all companies
    affected_companies = set()
    for fg_id in affected_fgs:
        fg = next((p for p in finished_goods if p['id'] == fg_id), None)
        if fg:
            affected_companies.add(fg['company_id'])
    
    supplier_reach[sid] = {
        'name': supplier['Name'],
        'rm_count': len(rms),
        'fg_count': len(affected_fgs),
        'company_count': len(affected_companies)
    }

top_supplier = max(supplier_reach.items(), key=lambda x: x[1]['company_count'])
print(f"  ✓ Top supplier reach: {top_supplier[1]['name']} ({top_supplier[1]['company_count']} companies)")

# ============================================================================
# 9. COMPANY SUPPLY CHAIN COMPLEXITY
# ============================================================================
print("\n[9/12] Analyzing company supply chains...")

company_supply_chains = {}
for company in companies:
    cid = company['Id']
    
    # Get company's finished goods
    company_fgs = [fg for fg in finished_goods if fg['company_id'] == cid]
    
    # Get all RMs used
    all_rms = set()
    for fg in company_fgs:
        all_rms.update(fg_to_rms.get(fg['id'], []))
    
    # Get all suppliers
    all_suppliers = set()
    for rm_id in all_rms:
        all_suppliers.update(rm_to_suppliers.get(rm_id, []))
    
    company_supply_chains[cid] = {
        'name': company['Name'],
        'fg_count': len(company_fgs),
        'rm_count': len(all_rms),
        'supplier_count': len(all_suppliers)
    }

most_complex = max(company_supply_chains.items(), key=lambda x: x[1]['rm_count'])
print(f"  ✓ Most complex: {most_complex[1]['name']} ({most_complex[1]['rm_count']} RMs, {most_complex[1]['supplier_count']} suppliers)")

# ============================================================================
# 10. PRODUCT METADATA ENRICHMENT
# ============================================================================
print("\n[10/12] Processing product metadata...")

product_metadata = {}
category_distribution = Counter()
certification_distribution = Counter()

for fg in finished_goods:
    fg_id = fg['id']
    metadata = {}
    
    # Get enrichment data
    if fg_id in enrichment_data:
        enrich = enrichment_data[fg_id]
        metadata['product_name'] = enrich.get('ProductName')
        metadata['brand'] = enrich.get('Brand')
    
    # Get standardization data
    if fg_id in standardization_data:
        std = standardization_data[fg_id]
        metadata['product_name'] = metadata.get('product_name') or std.get('ProductName')
        metadata['brand'] = metadata.get('brand') or std.get('Brand')
        metadata['category'] = std.get('ProductCategory')
        metadata['form'] = std.get('DosageForm')
        metadata['flavor'] = std.get('Flavor')
        
        if metadata['category']:
            category_distribution[metadata['category']] += 1
        
        # Parse dietary flags
        dietary_flags = std.get('DietaryFlags')
        if dietary_flags:
            try:
                import json as json_parser
                flags = json_parser.loads(dietary_flags) if isinstance(dietary_flags, str) else dietary_flags
                if isinstance(flags, list):
                    for flag in flags:
                        metadata[flag.lower()] = True
                        certification_distribution[flag.lower()] += 1
            except:
                pass
    
    # Get pricing data ⭐
    if fg_id in pricing_data:
        price = pricing_data[fg_id]
        metadata['price_usd'] = price.get('PriceUSD')
        metadata['price_source'] = price.get('PriceSource')
    
    product_metadata[fg_id] = metadata

print(f"  ✓ Products with enrichment: {len([m for m in product_metadata.values() if m.get('product_name')])}")
print(f"  ✓ Products with pricing: {len([m for m in product_metadata.values() if m.get('price_usd')])}")
if category_distribution:
    print(f"  ✓ Top categories: {category_distribution.most_common(5)}")

# ============================================================================
# 11. PRICING ANALYSIS ⭐ NEW!
# ============================================================================
print("\n[11/12] Analyzing pricing correlations... ⭐")

# Price by category
price_by_category = defaultdict(list)
for fg_id, meta in product_metadata.items():
    if meta.get('price_usd') and meta.get('category'):
        price_by_category[meta['category']].append(meta['price_usd'])

category_price_stats = {}
for cat, prices in price_by_category.items():
    if prices:
        category_price_stats[cat] = {
            'count': len(prices),
            'avg': sum(prices) / len(prices),
            'min': min(prices),
            'max': max(prices)
        }

if category_price_stats:
    print(f"  ✓ Categories with pricing:")
    for cat, stats in sorted(category_price_stats.items(), key=lambda x: x[1]['avg'], reverse=True)[:5]:
        print(f"    - {cat}: ${stats['avg']:.2f} avg (${stats['min']:.2f}-${stats['max']:.2f})")

# Price by brand
price_by_brand = defaultdict(list)
for fg_id, meta in product_metadata.items():
    if meta.get('price_usd') and meta.get('brand'):
        price_by_brand[meta['brand']].append(meta['price_usd'])

brand_price_stats = {}
for brand, prices in price_by_brand.items():
    if len(prices) >= 2:  # Only brands with 2+ products
        brand_price_stats[brand] = {
            'count': len(prices),
            'avg': sum(prices) / len(prices),
            'min': min(prices),
            'max': max(prices)
        }

# Price-risk correlation
priced_products_risk = []
for fg in high_risk_fgs:
    if fg['fg_id'] in product_metadata and product_metadata[fg['fg_id']].get('price_usd'):
        priced_products_risk.append({
            'fg_id': fg['fg_id'],
            'price': product_metadata[fg['fg_id']]['price_usd'],
            'risk_ratio': fg['risk_ratio'],
            'sku': fg['sku']
        })

if priced_products_risk:
    avg_price_high_risk = sum(p['price'] for p in priced_products_risk if p['risk_ratio'] >= 0.4) / max(1, len([p for p in priced_products_risk if p['risk_ratio'] >= 0.4]))
    avg_price_low_risk = sum(p['price'] for p in priced_products_risk if p['risk_ratio'] < 0.2) / max(1, len([p for p in priced_products_risk if p['risk_ratio'] < 0.2]))
    
    if avg_price_high_risk > 0 and avg_price_low_risk > 0:
        print(f"  ✓ Price-Risk Correlation:")
        print(f"    - High-risk products avg: ${avg_price_high_risk:.2f}")
        print(f"    - Low-risk products avg: ${avg_price_low_risk:.2f}")

# Similar products with price comparison
price_similarity_opportunities = []
for fg_a, fg_b, shared, jaccard in product_similarity[:50]:
    meta_a = product_metadata.get(fg_a, {})
    meta_b = product_metadata.get(fg_b, {})
    
    if meta_a.get('price_usd') and meta_b.get('price_usd') and jaccard >= 0.7:
        price_diff = abs(meta_a['price_usd'] - meta_b['price_usd'])
        if price_diff >= 5:  # Significant price difference
            price_similarity_opportunities.append({
                'fg_a': fg_a,
                'fg_b': fg_b,
                'name_a': meta_a.get('product_name', 'Unknown')[:40],
                'name_b': meta_b.get('product_name', 'Unknown')[:40],
                'price_a': meta_a['price_usd'],
                'price_b': meta_b['price_usd'],
                'price_diff': price_diff,
                'similarity': jaccard,
                'shared_materials': shared
            })

price_similarity_opportunities.sort(key=lambda x: x['price_diff'], reverse=True)
if price_similarity_opportunities:
    print(f"  ✓ Similar products with price differences: {len(price_similarity_opportunities)}")
    print(f"    - Biggest opportunity: ${price_similarity_opportunities[0]['price_diff']:.2f} difference")

# ============================================================================
# 12. EXPORT COMPREHENSIVE DATA
# ============================================================================
print("\n[12/12] Exporting comprehensive supply chain data...")

companies_export = [to_lowercase_keys(dict(c)) for c in companies]
suppliers_export = [to_lowercase_keys(dict(s)) for s in suppliers]

output = {
    'generated_at': datetime.now().isoformat(),
    'data_source': 'Filtered SQLite Database (db_filtered.sqlite) - Validated Supply Chains Only',
    'statistics': {
        'total_companies': len(companies),
        'total_suppliers': len(suppliers),
        'total_finished_goods': len(finished_goods),
        'total_raw_materials': len(raw_materials),
        'avg_rms_per_fg': sum(len(rms) for rms in fg_to_rms.values()) / len(fg_to_rms) if fg_to_rms else 0,
        'single_source_rms_count': len(single_source_rms),
        'multi_source_rms_count': len(multi_source_rms),
        'enriched_products_count': len([m for m in product_metadata.values() if m.get('product_name')]),
        'priced_products_count': len([m for m in product_metadata.values() if m.get('price_usd')])
    },
    'companies': companies_export,
    'suppliers': suppliers_export,
    'finished_goods': finished_goods,
    'raw_materials': raw_materials,
    'fg_to_rms': {str(k): v for k, v in fg_to_rms.items()},
    'rm_to_suppliers': {str(k): v for k, v in rm_to_suppliers.items()},
    'supplier_to_rms': {str(k): v for k, v in supplier_to_rms.items()},
    'critical_raw_materials': critical_raw_materials,
    'single_source_rms': single_source_rms,
    'high_risk_finished_goods': high_risk_fgs,
    'product_similarity': product_similarity,
    'supplier_reach': {str(k): v for k, v in supplier_reach.items()},
    'company_supply_chains': {str(k): v for k, v in company_supply_chains.items()},
    'product_metadata': {str(k): v for k, v in product_metadata.items()},
    'category_distribution': dict(category_distribution),
    'certification_distribution': dict(certification_distribution),
    'pricing_analysis': {
        'category_price_stats': category_price_stats,
        'brand_price_stats': brand_price_stats,
        'price_similarity_opportunities': price_similarity_opportunities[:20],
        'priced_products_risk': priced_products_risk
    }
}

with open(OUTPUT_PATH, 'w') as f:
    json.dump(output, f, indent=2)

file_size = len(json.dumps(output)) / 1024
print(f"\n✅ Exported to: {OUTPUT_PATH}")
print(f"   File size: {file_size:.1f} KB")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("ANALYSIS SUMMARY")
print("=" * 80)
print(f"Companies: {len(companies)}")
print(f"Suppliers: {len(suppliers)}")
print(f"Finished Goods: {len(finished_goods)}")
print(f"Raw Materials: {len(raw_materials)}")
print(f"\nSupply Chain Complexity:")
print(f"  Average RMs per FG: {output['statistics']['avg_rms_per_fg']:.1f}")
print(f"  Hub materials (5+ products): {len(hub_materials)}")
print(f"\nRisk Assessment:")
print(f"  Single-source RMs: {len(single_source_rms)}")
print(f"  High-risk products (>40%): {len([fg for fg in high_risk_fgs if fg['risk_ratio'] >= 0.4])}")
print(f"\nProduct Intelligence:")
print(f"  Similar product pairs: {len(product_similarity)}")
print(f"  Products with enrichment: {output['statistics']['enriched_products_count']}")
print(f"  Products with pricing: {output['statistics']['priced_products_count']} ⭐")
if category_distribution:
    print(f"  Top category: {category_distribution.most_common(1)[0]}")
print(f"\nSupplier Analysis:")
print(f"  Top supplier: {top_supplier[1]['name']} ({top_supplier[1]['company_count']} companies)")
print(f"  Most complex company: {most_complex[1]['name']} ({most_complex[1]['rm_count']} RMs)")
if price_similarity_opportunities:
    print(f"\n💰 Pricing Insights:")
    print(f"  Price optimization opportunities: {len(price_similarity_opportunities)}")
    print(f"  Biggest savings potential: ${price_similarity_opportunities[0]['price_diff']:.2f}")
print("=" * 80)

conn.close()
print("\n✅ Analysis complete! Ready for enhanced knowledge graph visualization!")

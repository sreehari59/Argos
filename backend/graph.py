"""
Knowledge Graph Builder:
- Build NetworkX directed graph from database
- Nodes: Company, Product (finished goods), Ingredient (canonical), Supplier
- Edges: owns, contains (with priority weight), supplies, substitutes
- Serialize to JSON for frontend consumption
"""
import json
from typing import Dict, List, Any

import networkx as nx

from db import query
from ingredients import parse_ingredient_name


def build_graph() -> nx.DiGraph:
    """Build the full knowledge graph from database tables."""
    G = nx.DiGraph()

    print("=== Building Knowledge Graph ===")

    # -----------------------------------------------------------------------
    # 1. Company nodes
    # -----------------------------------------------------------------------
    companies = query("SELECT Id, Name FROM Company")
    for c in companies:
        G.add_node(
            f"company:{c['Id']}",
            label=c['Name'],
            type='company',
            db_id=c['Id'],
        )
    print(f"  Companies: {len(companies)}")

    # -----------------------------------------------------------------------
    # 2. Product nodes (finished goods only)
    # -----------------------------------------------------------------------
    products = query("""
        SELECT p.Id, p.SKU, p.CompanyId, c.Name as CompanyName
        FROM Product p
        JOIN Company c ON p.CompanyId = c.Id
        WHERE p.Type = 'finished-good'
    """)
    for p in products:
        G.add_node(
            f"product:{p['Id']}",
            label=p['SKU'],
            type='product',
            db_id=p['Id'],
            company_id=p['CompanyId'],
            company_name=p['CompanyName'],
        )
        # Edge: company --owns--> product
        G.add_edge(
            f"company:{p['CompanyId']}",
            f"product:{p['Id']}",
            type='owns',
            weight=1.0,
        )
    print(f"  Products (finished goods): {len(products)}")

    # -----------------------------------------------------------------------
    # 3. Ingredient nodes (canonical families)
    # -----------------------------------------------------------------------
    families = query("""
        SELECT DISTINCT family_name, family_type
        FROM Ingredient_Family
    """)
    family_set = set()
    for f in families:
        fn = f['family_name']
        if fn not in family_set:
            G.add_node(
                f"ingredient:{fn}",
                label=fn,
                type='ingredient',
                family_type=f['family_type'],
            )
            family_set.add(fn)
    print(f"  Ingredient families: {len(family_set)}")

    # -----------------------------------------------------------------------
    # 4. BOM edges: product --contains--> ingredient (with functional role)
    # -----------------------------------------------------------------------
    try:
        bom_rows = query("""
            SELECT ir.product_id, ir.ingredient_id, ir.canonical_name,
                   ir.functional_role, ir.confidence,
                   ifm.family_id
            FROM Ingredient_Role ir
            LEFT JOIN Ingredient_Family_Member ifm
                ON ir.ingredient_id = ifm.product_id
        """)
    except:
        # Fallback: use BOM_Component without roles
        bom_rows = query("""
            SELECT bc.BOMId, b.ProducedProductId as product_id, 
                   bc.ConsumedProductId as ingredient_id,
                   ifam.canonical_name,
                   ifm.family_id
            FROM BOM_Component bc
            JOIN BOM b ON bc.BOMId = b.Id
            LEFT JOIN Ingredient_Family_Member ifm ON bc.ConsumedProductId = ifm.product_id
            LEFT JOIN Ingredient_Family ifam ON ifm.family_id = ifam.Id
        """)

    # Get family name lookup
    family_name_lookup = {}
    family_rows = query("SELECT Id, canonical_name, family_name FROM Ingredient_Family")
    for fr in family_rows:
        family_name_lookup[fr['Id']] = fr['family_name']

    # Get ingredient priority from enrichment
    try:
        priority_data = query("""
            SELECT product_id, ingredient_priority_json
            FROM Clean_Enrichment
            WHERE ingredient_priority_json IS NOT NULL
        """)
        product_priorities = {}
        for pd in priority_data:
            try:
                ingredients_list = json.loads(pd['ingredient_priority_json'])
                product_priorities[pd['product_id']] = ingredients_list
            except (json.JSONDecodeError, TypeError):
                pass
    except:
        # No enrichment data available
        product_priorities = {}

    bom_edge_count = 0
    for row in bom_rows:
        family_name = family_name_lookup.get(row.get('family_id'), row.get('canonical_name', 'unknown'))
        if not family_name:
            continue
            
        ingredient_node = f"ingredient:{family_name}"

        if not G.has_node(ingredient_node):
            G.add_node(
                ingredient_node,
                label=family_name,
                type='ingredient',
                family_type='exact_match',
            )

        # Calculate priority weight from ingredient order
        priority_weight = 0.5  # default
        product_id = row['product_id']
        canonical_name = row.get('canonical_name')
        if product_id in product_priorities and canonical_name:
            ingredients_list = product_priorities[product_id]
            for i, label_ing in enumerate(ingredients_list):
                if canonical_name.replace('-', ' ').lower() in label_ing.lower():
                    priority_weight = 1.0 / (i + 1)
                    break

        product_node = f"product:{row['product_id']}"
        G.add_edge(
            product_node,
            ingredient_node,
            type='contains',
            functional_role=row.get('functional_role', 'unknown'),
            confidence=row.get('confidence', 1.0),
            priority_weight=priority_weight,
        )
        bom_edge_count += 1

    print(f"  BOM edges (product→ingredient): {bom_edge_count}")

    # -----------------------------------------------------------------------
    # 5. Supplier nodes and edges
    # -----------------------------------------------------------------------
    suppliers = query("SELECT Id, Name FROM Supplier")
    for s in suppliers:
        G.add_node(
            f"supplier:{s['Id']}",
            label=s['Name'],
            type='supplier',
            db_id=s['Id'],
        )
    print(f"  Suppliers: {len(suppliers)}")

    # Supplier --supplies--> ingredient
    supply_rows = query("""
        SELECT sp.SupplierId, sp.ProductId, p.SKU
        FROM Supplier_Product sp
        JOIN Product p ON sp.ProductId = p.Id
        WHERE p.Type = 'raw-material'
    """)

    supply_edge_count = 0
    for row in supply_rows:
        canonical_name = parse_ingredient_name(row['SKU'])
        # Find the family for this ingredient
        family_info = query(
            "SELECT family_name FROM Ingredient_Family WHERE canonical_name = ? LIMIT 1",
            (canonical_name,)
        )
        if family_info:
            family_name = family_info[0]['family_name']
        else:
            family_name = canonical_name

        ingredient_node = f"ingredient:{family_name}"
        if G.has_node(ingredient_node):
            edge_key = (f"supplier:{row['SupplierId']}", ingredient_node)
            if not G.has_edge(*edge_key):
                G.add_edge(
                    *edge_key,
                    type='supplies',
                    weight=1.0,
                )
                supply_edge_count += 1

    print(f"  Supply edges (supplier→ingredient): {supply_edge_count}")

    # -----------------------------------------------------------------------
    # 6. Substitution edges: ingredient --substitutes--> ingredient
    # -----------------------------------------------------------------------
    # Since ingredients are stored as family-level nodes, substitution edges
    # connect family nodes that belong to a broader substitute group.
    # 
    # Strategy: for each non-exact-match family, its canonical_names each map
    # to a family_name node. If multiple distinct family_name nodes exist in
    # the same broader group, connect them.
    #
    # However, in our current design, all canonical names in a form_variant
    # or functional_substitute family map to the SAME family_name node.
    # So instead, we store substitution info as node metadata AND create
    # cross-family substitution edges where applicable.

    sub_edge_count = 0

    # Annotate ingredient nodes with their substitution families
    for fn in family_set:
        fam_info = query(
            "SELECT DISTINCT family_type FROM Ingredient_Family WHERE family_name = ? LIMIT 1",
            (fn,)
        )
        if fam_info:
            ft = fam_info[0]['family_type']
            if ft in ('form_variant', 'functional_substitute'):
                # Get all canonical names in this family
                members = query(
                    "SELECT DISTINCT canonical_name FROM Ingredient_Family WHERE family_name = ?",
                    (fn,)
                )
                member_names = [m['canonical_name'] for m in members]
                G.nodes[f"ingredient:{fn}"]['substitutable_names'] = member_names
                G.nodes[f"ingredient:{fn}"]['substitution_type'] = ft

    # Now find cross-family substitution opportunities:
    # ingredients that share a functional role and are in related families
    # (e.g., lecithin-emulsifiers family connects soy-lecithin and sunflower-lecithin)
    from ingredients import FORM_VARIANT_FAMILIES, FUNCTIONAL_SUBSTITUTE_GROUPS

    # Build reverse lookup: canonical_name -> family_name (graph node name)
    cn_to_graph_node = {}
    for row in family_rows:
        cn_to_graph_node[row['canonical_name']] = row['family_name']

    # For each substitute group, connect the graph nodes
    all_groups = {**FORM_VARIANT_FAMILIES, **FUNCTIONAL_SUBSTITUTE_GROUPS}
    for group_name, members in all_groups.items():
        # Find which graph nodes these members map to
        graph_nodes = set()
        for member in members:
            if member in cn_to_graph_node:
                graph_nodes.add(cn_to_graph_node[member])

        # Connect distinct graph nodes within this group
        graph_nodes = [f"ingredient:{n}" for n in graph_nodes if G.has_node(f"ingredient:{n}")]
        is_form = group_name in FORM_VARIANT_FAMILIES
        for i in range(len(graph_nodes)):
            for j in range(i + 1, len(graph_nodes)):
                if not G.has_edge(graph_nodes[i], graph_nodes[j]):
                    G.add_edge(
                        graph_nodes[i], graph_nodes[j],
                        type='substitutes',
                        weight=0.8 if is_form else 0.6,
                        family_name=group_name,
                        family_type='form_variant' if is_form else 'functional_substitute',
                    )
                    G.add_edge(
                        graph_nodes[j], graph_nodes[i],
                        type='substitutes',
                        weight=0.8 if is_form else 0.6,
                        family_name=group_name,
                        family_type='form_variant' if is_form else 'functional_substitute',
                    )
                    sub_edge_count += 2

    print(f"  Substitution edges: {sub_edge_count}")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print(f"\n  Graph summary:")
    print(f"    Nodes: {G.number_of_nodes()}")
    print(f"    Edges: {G.number_of_edges()}")

    node_types = {}
    for _, data in G.nodes(data=True):
        t = data.get('type', 'unknown')
        node_types[t] = node_types.get(t, 0) + 1
    for t, c in sorted(node_types.items()):
        print(f"      {t}: {c}")

    edge_types = {}
    for _, _, data in G.edges(data=True):
        t = data.get('type', 'unknown')
        edge_types[t] = edge_types.get(t, 0) + 1
    for t, c in sorted(edge_types.items()):
        print(f"      {t}: {c}")

    return G


def graph_to_json(G: nx.DiGraph) -> Dict[str, Any]:
    """Convert NetworkX graph to JSON-serializable dict for frontend."""
    nodes = []
    for node_id, data in G.nodes(data=True):
        nodes.append({
            'id': node_id,
            'label': data.get('label', node_id),
            'type': data.get('type', 'unknown'),
            'metadata': {k: v for k, v in data.items() if k not in ('label', 'type')},
        })

    edges = []
    for source, target, data in G.edges(data=True):
        edges.append({
            'source': source,
            'target': target,
            'type': data.get('type', 'unknown'),
            'weight': data.get('weight', 1.0),
            'metadata': {k: v for k, v in data.items() if k not in ('type', 'weight')},
        })

    return {'nodes': nodes, 'edges': edges}


# Global graph instance (built once, reused by API)
_graph = None
_graph_json = None


def get_graph() -> nx.DiGraph:
    """Get or build the graph singleton."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def get_graph_json() -> Dict[str, Any]:
    """Get or build the graph JSON singleton."""
    global _graph_json
    if _graph_json is None:
        _graph_json = graph_to_json(get_graph())
    return _graph_json


if __name__ == "__main__":
    G = build_graph()
    data = graph_to_json(G)
    print(f"\nJSON output: {len(data['nodes'])} nodes, {len(data['edges'])} edges")

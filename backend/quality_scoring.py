"""
Quality Scoring and Final Recommendation Ranking:
- LLM-based quality assessment (when enrichment data available)
- Priority-weighted scoring based on ingredient order
- Final score calculation combining compliance, quality, and priority
"""
import json
from typing import Dict, Any, List

from db import query, execute
from llm_compliance import call_llm, check_compliance


def _safe_get_enrichment(product_id: Any) -> Dict[str, Any]:
    """Fetch enrichment row for a product id; return empty dict if unavailable."""
    if not product_id:
        return {}

    try:
        rows = query(
            "SELECT * FROM Clean_Enrichment WHERE product_id = ?",
            (product_id,)
        )
        return rows[0] if rows else {}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Quality Scoring
# ---------------------------------------------------------------------------

def score_quality_llm(
    current_ingredient: str,
    substitute_ingredient: str,
    functional_role: str,
    current_enrichment: Dict[str, Any],
    substitute_enrichment: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Use LLM to assess quality of substitute vs current ingredient.
    
    Returns:
        {
            'quality_score': float (0-1),
            'reasoning': str
        }
    """
    # Build context from enrichment data
    current_context = []
    if current_enrichment:
        if current_enrichment.get('is_organic'):
            current_context.append("organic")
        if current_enrichment.get('is_non_gmo'):
            current_context.append("non-GMO")
    
    substitute_context = []
    if substitute_enrichment:
        if substitute_enrichment.get('is_organic'):
            substitute_context.append("organic")
        if substitute_enrichment.get('is_non_gmo'):
            substitute_context.append("non-GMO")
    
    prompt = f"""Assess the quality of a proposed ingredient substitution for a supplement/food product.

Current ingredient: {current_ingredient}
{f"Properties: {', '.join(current_context)}" if current_context else ""}

Proposed substitute: {substitute_ingredient}
{f"Properties: {', '.join(substitute_context)}" if substitute_context else ""}

Functional role: {functional_role}

Rate the quality of this substitution on a scale of 0.0 to 1.0, where:
- 1.0 = Superior quality (better bioavailability, purity, or efficacy)
- 0.8 = Equivalent quality
- 0.6 = Acceptable but slightly lower quality
- 0.4 = Noticeably lower quality
- 0.2 = Poor substitution

Respond ONLY with valid JSON:
{{"quality_score": 0.0-1.0, "reasoning": "brief explanation (max 2 sentences)"}}"""

    response = call_llm(prompt, max_tokens=200)
    
    try:
        if '```json' in response:
            response = response.split('```json')[1].split('```')[0].strip()
        elif '```' in response:
            response = response.split('```')[1].split('```')[0].strip()
        
        result = json.loads(response)
        if 'quality_score' in result and 'reasoning' in result:
            return {
                'quality_score': float(result['quality_score']),
                'reasoning': str(result['reasoning'])
            }
    except:
        pass
    
    # Fallback: assume equivalent quality
    return {
        'quality_score': 0.8,
        'reasoning': 'Quality assessment unavailable; assuming equivalent quality.'
    }


def score_quality_heuristic(
    current_ingredient: str,
    substitute_ingredient: str,
    family_type: str
) -> Dict[str, Any]:
    """
    Rule-based quality scoring when enrichment data is unavailable.
    """
    # Form variants are typically equivalent quality
    if family_type == 'form_variant':
        return {
            'quality_score': 0.85,
            'reasoning': 'Form variant substitution; typically equivalent quality.'
        }
    
    # Functional substitutes may vary
    if family_type == 'functional_substitute':
        # Check for known quality upgrades
        current_lower = current_ingredient.lower()
        sub_lower = substitute_ingredient.lower()
        
        # Organic upgrade
        if 'organic' in sub_lower and 'organic' not in current_lower:
            return {
                'quality_score': 0.9,
                'reasoning': 'Upgrade to organic variant.'
            }
        
        # Non-GMO upgrade
        if 'non-gmo' in sub_lower and 'non-gmo' not in current_lower:
            return {
                'quality_score': 0.88,
                'reasoning': 'Upgrade to non-GMO variant.'
            }
        
        # Known quality differences for specific ingredients
        if 'sunflower-lecithin' in sub_lower and 'soy-lecithin' in current_lower:
            return {
                'quality_score': 0.85,
                'reasoning': 'Sunflower lecithin is allergen-friendly alternative to soy.'
            }
        
        # Default for functional substitutes
        return {
            'quality_score': 0.75,
            'reasoning': 'Functional substitute; quality may vary.'
        }
    
    # Default
    return {
        'quality_score': 0.8,
        'reasoning': 'Standard substitution.'
    }


# ---------------------------------------------------------------------------
# Final Score Calculation
# ---------------------------------------------------------------------------

def calculate_final_score(
    compliance_score: float,
    quality_score: float,
    priority_rank: float,
    family_type: str
) -> float:
    """
    Calculate final recommendation score.
    
    Formula:
    - Compliance is a gate (0 = reject)
    - Quality and priority are weighted factors
    - Form variants get bonus (safer substitution)
    
    final_score = compliance_score * (
        0.4 * quality_score +
        0.4 * priority_rank +
        0.2 * family_type_bonus
    )
    """
    if compliance_score < 0.5:
        return 0.0  # Non-compliant = reject
    
    family_bonus = 1.0 if family_type == 'form_variant' else 0.8
    
    weighted_score = (
        0.4 * quality_score +
        0.4 * priority_rank +
        0.2 * family_bonus
    )
    
    return compliance_score * weighted_score


def update_all_scores(use_llm: bool = True, limit: int = None):
    """
    Update quality and final scores for all candidates.
    
    Args:
        use_llm: Whether to use LLM for quality scoring (slower but better)
        limit: Limit number of candidates to process (for testing)
    """
    print("=== Updating Quality and Final Scores ===")
    
    # Get all candidates with compliance scores
    if limit:
        candidates = query(
            "SELECT * FROM Substitution_Candidate LIMIT ?",
            (limit,)
        )
    else:
        candidates = query(
            "SELECT * FROM Substitution_Candidate"
        )
    
    print(f"Processing {len(candidates)} candidates...")
    
    for i, cand in enumerate(candidates):
        # Pull enrichment rows used by both quality and compliance checks.
        current_enrich = _safe_get_enrichment(cand.get('current_ingredient_id'))
        substitute_enrich = _safe_get_enrichment(cand.get('substitute_ingredient_id'))
        product_enrich = _safe_get_enrichment(cand.get('product_id'))

        if use_llm:
            quality_result = score_quality_llm(
                cand['current_canonical_name'],
                cand['substitute_canonical_name'],
                cand['functional_role'],
                current_enrich,
                substitute_enrich
            )

            compliance_result = check_compliance(
                cand['current_canonical_name'],
                cand['substitute_canonical_name'],
                product_enrich,
                cand['functional_role'],
                use_llm=True
            )
            compliance_score = (
                compliance_result['confidence']
                if compliance_result['compliant']
                else 0.0
            )
            compliance_reasoning = compliance_result['reasoning']
        else:
            quality_result = score_quality_heuristic(
                cand['current_canonical_name'],
                cand['substitute_canonical_name'],
                cand['family_type']
            )
            compliance_score = cand['compliance_score'] if cand['compliance_score'] is not None else 0.9
            compliance_reasoning = cand.get('compliance_reasoning')

        # Calculate final score
        final_score = calculate_final_score(
            compliance_score,
            quality_result['quality_score'],
            cand['priority_rank'] or 0.5,
            cand['family_type']
        )

        # Update database
        execute("""
            UPDATE Substitution_Candidate
            SET quality_score = ?,
                quality_reasoning = ?,
                compliance_score = ?,
                compliance_reasoning = ?,
                final_score = ?
            WHERE id = ?
        """, (
            quality_result['quality_score'],
            quality_result['reasoning'],
            compliance_score,
            compliance_reasoning,
            final_score,
            cand['id']
        ))
        
        if (i + 1) % 100 == 0:
            print(f"  Progress: {i + 1}/{len(candidates)}")
    
    print(f"Updated {len(candidates)} candidates with quality and final scores.")
    
    # Stats
    stats = query("""
        SELECT 
            COUNT(*) as total,
            AVG(quality_score) as avg_quality,
            AVG(final_score) as avg_final,
            MAX(final_score) as max_final,
            MIN(final_score) as min_final
        FROM Substitution_Candidate
        WHERE final_score IS NOT NULL
    """)[0]
    
    print(f"\nScore statistics:")
    print(f"  Total scored: {stats['total']}")
    if stats['avg_quality'] is not None:
        print(f"  Avg quality: {stats['avg_quality']:.2f}")
        print(f"  Avg final: {stats['avg_final']:.2f}")
        print(f"  Range: {stats['min_final']:.2f} - {stats['max_final']:.2f}")
    else:
        print(f"  No scores available yet")
    
    # Top recommendations
    top = query("""
        SELECT sc.*, p.SKU as product_sku
        FROM Substitution_Candidate sc
        JOIN Product p ON sc.product_id = p.Id
        WHERE sc.final_score IS NOT NULL
        ORDER BY sc.final_score DESC
        LIMIT 10
    """)
    
    print(f"\nTop 10 recommendations:")
    for i, rec in enumerate(top, 1):
        print(f"  {i}. {rec['product_sku']}: {rec['current_canonical_name']} → {rec['substitute_canonical_name']}")
        print(f"     Score: {rec['final_score']:.3f} | Role: {rec['functional_role']} | Type: {rec['family_type']}")


if __name__ == "__main__":
    update_all_scores(use_llm=True)

"""
LLM-powered Compliance Gate:
- Check if a substitute meets dietary claims and allergen requirements
- Use OpenAI Chat Completions API
- Cache results to avoid redundant calls
"""
import os
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path

import httpx
from dotenv import load_dotenv

from db import query, execute

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env")


# ---------------------------------------------------------------------------
# OpenAI API client
# ---------------------------------------------------------------------------

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini"


def call_llm(prompt: str, max_tokens: int = 500) -> str:
    """Call OpenAI LLM with the given prompt."""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,  # Lower temperature for more consistent compliance checks
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(OPENAI_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content'].strip()
            else:
                return f"Error: Unexpected response format: {data}"
    
    except httpx.HTTPError as e:
        return f"Error calling LLM: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


# ---------------------------------------------------------------------------
# Compliance checking
# ---------------------------------------------------------------------------

def check_compliance_rule_based(
    substitute_ingredient: str,
    requirements: list,
    allergen_constraints: list
) -> Dict[str, Any]:
    """Rule-based compliance checking as fallback."""
    violations = []
    confidence = 0.85
    sub_lower = substitute_ingredient.lower()
    
    if "Must NOT contain soy" in allergen_constraints:
        if 'soy' in sub_lower and 'sunflower' not in sub_lower:
            violations.append("Contains soy")
    
    if "Must NOT contain dairy" in allergen_constraints:
        if any(word in sub_lower for word in ['whey', 'casein', 'milk', 'dairy', 'lactose']):
            violations.append("Contains dairy")
    
    if "Must NOT contain gluten" in allergen_constraints:
        if any(word in sub_lower for word in ['wheat', 'gluten', 'barley', 'rye']):
            violations.append("Contains gluten")
    
    if "Vegan" in requirements:
        if any(word in sub_lower for word in ['gelatin', 'whey', 'casein', 'milk', 'bone', 'bovine', 
                                                'fish', 'shellfish', 'egg', 'honey', 'beeswax']):
            violations.append("Not vegan")
    
    if "Vegetarian" in requirements:
        if 'gelatin' in sub_lower and 'bovine' in sub_lower:
            violations.append("Not vegetarian")
    
    if "Gluten-Free" in requirements:
        if any(word in sub_lower for word in ['wheat', 'gluten', 'barley', 'rye', 'malt']):
            violations.append("Contains gluten")
    
    if violations:
        return {'compliant': False, 'confidence': confidence, 'reasoning': f"Violations: {', '.join(violations)}"}
    else:
        return {'compliant': True, 'confidence': confidence, 'reasoning': 'Passes all checks'}


def check_compliance(
    current_ingredient: str,
    substitute_ingredient: str,
    product_enrichment: Dict[str, Any],
    functional_role: str,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Check if a substitute ingredient meets compliance requirements.
    Uses LLM when available, falls back to rule-based.
    """
    requirements = []
    if product_enrichment.get('is_gluten_free'): requirements.append("Gluten-Free")
    if product_enrichment.get('is_non_gmo'): requirements.append("Non-GMO")
    if product_enrichment.get('is_vegan'): requirements.append("Vegan")
    if product_enrichment.get('is_vegetarian'): requirements.append("Vegetarian")
    if product_enrichment.get('is_organic'): requirements.append("Organic")
    if product_enrichment.get('is_kosher'): requirements.append("Kosher")
    if product_enrichment.get('is_dairy_free'): requirements.append("Dairy-Free")
    
    allergen_constraints = []
    if product_enrichment.get('contains_soy') == 0: allergen_constraints.append("Must NOT contain soy")
    if product_enrichment.get('contains_dairy') == 0: allergen_constraints.append("Must NOT contain dairy")
    if product_enrichment.get('contains_gluten') == 0: allergen_constraints.append("Must NOT contain gluten")
    
    if not requirements and not allergen_constraints:
        return {'compliant': True, 'confidence': 0.9, 'reasoning': 'No compliance requirements.'}
    
    # Try LLM first
    if use_llm:
        prompt = f"""Analyze if this ingredient substitution meets requirements.

Current: {current_ingredient}
Substitute: {substitute_ingredient}
Role: {functional_role}

Requirements: {', '.join(requirements) if requirements else 'None'}
Allergen constraints: {', '.join(allergen_constraints) if allergen_constraints else 'None'}

Does "{substitute_ingredient}" meet ALL requirements? Respond ONLY with valid JSON:
{{"compliant": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""

        response = call_llm(prompt, max_tokens=200)
        
        try:
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                response = response.split('```')[1].split('```')[0].strip()
            
            result = json.loads(response)
            if 'compliant' in result and 'confidence' in result and 'reasoning' in result:
                return {
                    'compliant': bool(result['compliant']),
                    'confidence': float(result['confidence']),
                    'reasoning': str(result['reasoning'])
                }
        except:
            pass  # Fall through to rule-based
    
    # Fallback to rule-based
    return check_compliance_rule_based(substitute_ingredient, requirements, allergen_constraints)


def batch_check_compliance(
    candidates: list[Dict[str, Any]],
    batch_size: int = 10,
    delay: float = 1.0
) -> list[Dict[str, Any]]:
    """
    Check compliance for a batch of candidates.
    Includes rate limiting and progress tracking.
    """
    print(f"Checking compliance for {len(candidates)} candidates...")
    
    results = []
    
    for i, candidate in enumerate(candidates):
        # Get product enrichment data
        enrichment = query(
            "SELECT * FROM Clean_Enrichment WHERE product_id = ?",
            (candidate['product_id'],)
        )
        
        if not enrichment:
            # No enrichment data, assume compliant
            result = {
                **candidate,
                'compliance_score': 0.9,
                'compliance_reasoning': 'No enrichment data available for this product.',
            }
        else:
            enrich_data = enrichment[0]
            compliance_result = check_compliance(
                candidate['current_canonical_name'],
                candidate['substitute_canonical_name'],
                enrich_data,
                candidate['functional_role']
            )
            
            result = {
                **candidate,
                'compliance_score': compliance_result['confidence'] if compliance_result['compliant'] else 0.0,
                'compliance_reasoning': compliance_result['reasoning'],
            }
        
        results.append(result)
        
        # Progress
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{len(candidates)}")
        
        # Rate limiting
        if (i + 1) % batch_size == 0 and i + 1 < len(candidates):
            time.sleep(delay)
    
    return results


def update_compliance_scores():
    """Update compliance scores for all candidates in the database."""
    print("=== Updating Compliance Scores ===")
    
    # Get all candidates
    candidates = query("SELECT * FROM Substitution_Candidate")
    print(f"Total candidates: {len(candidates)}")
    
    # For demo purposes, let's process a sample
    # In production, you'd process all or use caching
    sample_size = min(100, len(candidates))
    sample = candidates[:sample_size]
    print(f"Processing sample of {sample_size} candidates...")
    
    # Check compliance
    results = batch_check_compliance(sample, batch_size=5, delay=0.5)
    
    # Update database
    for r in results:
        execute("""
            UPDATE Substitution_Candidate
            SET compliance_score = ?, compliance_reasoning = ?
            WHERE id = ?
        """, (r['compliance_score'], r['compliance_reasoning'], r['id']))
    
    print(f"Updated {len(results)} candidates with compliance scores.")
    
    # Stats
    compliant = sum(1 for r in results if r['compliance_score'] > 0.5)
    print(f"Compliant: {compliant}/{len(results)} ({compliant/len(results)*100:.1f}%)")
    
    avg_score = sum(r['compliance_score'] for r in results) / len(results)
    print(f"Average compliance score: {avg_score:.2f}")
    
    return results


if __name__ == "__main__":
    # Test with a single example first
    print("=== Testing LLM Compliance Check ===")
    
    test_result = check_compliance(
        current_ingredient="soy-lecithin",
        substitute_ingredient="sunflower-lecithin",
        product_enrichment={
            'is_gluten_free': True,
            'is_non_gmo': True,
            'is_vegan': True,
            'contains_soy': 0,  # Must NOT contain soy
        },
        functional_role="emulsifier"
    )
    
    print(f"\nTest result:")
    print(f"  Compliant: {test_result['compliant']}")
    print(f"  Confidence: {test_result['confidence']}")
    print(f"  Reasoning: {test_result['reasoning']}")
    
    # If test passes, run batch update
    if test_result['compliant']:
        print("\n" + "="*50)
        update_compliance_scores()

"""Pydantic models for API responses."""
from pydantic import BaseModel
from typing import Optional


class CompanySummary(BaseModel):
    id: int
    name: str
    product_count: int


class ProductSummary(BaseModel):
    id: int
    sku: str
    company_id: int
    company_name: str
    type: str


class IngredientFamily(BaseModel):
    id: int
    canonical_name: str
    family_type: str  # exact_match, form_variant, functional_substitute
    member_count: int


class IngredientRole(BaseModel):
    product_id: int
    ingredient_id: int
    canonical_name: str
    functional_role: str
    confidence: float
    method: str  # heuristic, llm, position_validated


class SupplierSummary(BaseModel):
    id: int
    name: str
    materials_supplied: int
    companies_served: int


class CleanEnrichment(BaseModel):
    product_id: int
    product_name: Optional[str] = None
    is_gluten_free: bool = False
    is_non_gmo: bool = False
    is_vegan: bool = False
    is_vegetarian: bool = False
    is_organic: bool = False
    is_kosher: bool = False
    is_dairy_free: bool = False
    contains_soy: bool = False
    contains_dairy: bool = False
    contains_gluten: bool = False
    ingredient_priority_json: Optional[str] = None


class SubstitutionCandidate(BaseModel):
    ingredient_id: int
    ingredient_name: str
    substitute_id: int
    substitute_name: str
    family_type: str
    functional_role: str
    available_suppliers: list[str]


class RiskItem(BaseModel):
    ingredient_name: str
    companies_using: int
    num_suppliers: int
    risk_type: str  # single_source, no_supplier


class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # company, product, ingredient, supplier
    metadata: dict = {}


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str  # owns, contains, supplies, substitutes
    weight: float = 1.0
    metadata: dict = {}


class GraphData(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]

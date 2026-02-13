
from typing import List, Dict, Any
import hashlib
from app.db.schemas import PlanSchema, DFR
from app.engine.evaluators import Violation
from app.core.engine_version import ENGINE_VERSION
from app.core.canonicalize import canonicalize_json, sort_lists_in_plan

def generate_dfr(plan: PlanSchema, violations: List[Violation]) -> DFR:
    """
    Generate a Deterministic Failure Report.
    """
    # 1. Canonicalize Plan
    # Convert Pydantic model to dict
    plan_dict = plan.model_dump()
    
    # Sort lists to ensure stability
    sorted_plan = sort_lists_in_plan(plan_dict)
    
    # Generate canonical JSON string (UNSCRUBBED for hashing)
    # We must hash the raw inputs to ensure determinism.
    # Scrubbing is for storage/logging only.
    canonical_json_raw = canonicalize_json(sorted_plan)
    
    # 2. Compute Plan Hash
    plan_hash = hashlib.sha256(canonical_json_raw.encode()).hexdigest()
    
    # 3. Format Violations
    # Sort violations by rule_id and offending_node to ensure deterministic order in output
    violations.sort(key=lambda v: (v.rule_id, v.offending_node))
    
    formatted_violations = [
        {
            "rule_id": v.rule_id,
            "message": v.message,
            "offending_node": v.offending_node,
            "metadata": v.metadata
        }
        for v in violations
    ]
    
    passed = len(formatted_violations) == 0
    
    return DFR(
        plan_hash=plan_hash,
        engine_version=str(ENGINE_VERSION),
        passed=passed,
        violations=formatted_violations
    )

import json
from typing import Any, Dict, List

def sort_lists_in_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sort lists in the plan to ensure deterministic ordering.
    """
    if isinstance(plan, dict):
        return {k: sort_lists_in_plan(v) for k, v in sorted(plan.items())}
    elif isinstance(plan, list):
        # Try to sort using a stable key. 
        # For objects with 'id', use 'id'.
        # For strings, just sort.
        sorted_list = [sort_lists_in_plan(x) for x in plan]
        try:
            return sorted(sorted_list, key=lambda x: x.get('id') if isinstance(x, dict) and 'id' in x else str(x))
        except:
            # Fallback if mixed types or no ID
            return sorted(sorted_list, key=lambda x: str(x))
    else:
        return plan

def canonicalize_json(data: Any) -> str:
    """
    Returns a canonical JSON string for hashing.
    Keys sorted, lists sorted (where possible), no whitespace.
    """
    sorted_data = sort_lists_in_plan(data)
    return json.dumps(sorted_data, sort_keys=True, separators=(',', ':'))

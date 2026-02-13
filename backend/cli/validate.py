
import sys
import json
import argparse
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.schemas import PlanSchema
from app.engine.builder import Builder, BuildError
from app.engine.evaluators import ACTIVE_EVALUATORS
from app.engine.dfr import generate_dfr
from app.core.engine_version import ENGINE_VERSION

def main():
    parser = argparse.ArgumentParser(description="Deterministic Architecture Validator")
    parser.add_argument("plan_file", help="Path to input plan JSON file")
    parser.add_argument("--json", action="store_true", help="Output only JSON DFR", default=True)
    
    args = parser.parse_args()
    
    try:
        # 1. Load Plan
        plan_path = Path(args.plan_file)
        if not plan_path.exists():
            print(f"Error: File not found: {plan_path}", file=sys.stderr)
            sys.exit(2)
            
        with open(plan_path, 'r') as f:
            data = json.load(f)
            
        # Parse into Pydantic model
        try:
            plan = PlanSchema(**data)
        except Exception as e:
            print(f"Error: Invalid Plan Schema: {e}", file=sys.stderr)
            sys.exit(2)

        # 2. Build Graph
        builder = Builder()
        try:
            graph = builder.build(plan)
        except BuildError as e:
            print(json.dumps({
                "error": "BuildError",
                "detail": str(e),
                "engine_version": str(ENGINE_VERSION)
            }, indent=2))
            sys.exit(1)

        # 3. Evaluate
        violations = []
        for evaluator in ACTIVE_EVALUATORS:
            violations.extend(evaluator.evaluate(graph))

        # 4. Generate DFR
        dfr = generate_dfr(plan, violations)
        # Inject current engine version
        dfr.engine_version = str(ENGINE_VERSION) # from module

        # 5. Output
        print(dfr.model_dump_json(indent=2))
        
        # 6. Exit Code
        sys.exit(0 if dfr.passed else 1)

    except Exception as e:
        print(f"Internal Error: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()

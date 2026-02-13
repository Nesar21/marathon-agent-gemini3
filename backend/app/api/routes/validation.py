
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.api.routes.auth import get_current_user, get_db
from app.db.models import User, ValidationResult, AuditLog
from app.db.schemas import PlanSchema, DFR
from app.engine.builder import Builder, BuildError
from app.engine.evaluators import ACTIVE_EVALUATORS
from app.engine.dfr import generate_dfr
from app.core.engine_version import ENGINE_VERSION
from app.core.canonicalize import canonicalize_json
import json
import uuid

router = APIRouter()

def create_audit_log(db: Session, user_id: uuid.UUID, request_id: uuid.UUID, status: str, violation_count: int):
    """
    Helper to create audit log entry.
    """
    audit = AuditLog(
        request_id=request_id,
        user_id=user_id,
        action="validate_plan",
        action_type="validation",
        status=status,
        violations_count=violation_count
    )
    db.add(audit)
    try:
        db.commit()
    except Exception:
        db.rollback()
        # Log error but don't fail request?
        pass

@router.post("/", response_model=DFR)
def validate_plan(
    plan: PlanSchema,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate a plan against architectural rules.
    Deterministically generates DFR.
    Idempotent: Returns cached result if plan+engine matches.
    """
    request_id = uuid.uuid4()
    
    # 1. Build Graph & Reject Ambiguity
    builder = Builder()
    try:
        graph = builder.build(plan)
    except BuildError as e:
        # Taxonomy: Build Failure (Ambiguity, Invalid Structure) -> 400
        # This is NOT a rule violation. It means the plan cannot be compiled to a graph.
        raise HTTPException(
            status_code=400, 
            detail={
                "type": "compilation_error",
                "message": f"Plan Compilation Failed: {str(e)}",
                "help": "Ensure no duplicate IDs, circular dependencies, or invalid references."
            }
        )
    except Exception as e:
        # Taxonomy: System Failure -> 500
        raise HTTPException(
            status_code=500, 
            detail={
                "type": "system_error",
                "message": f"Internal Engine Failure: {str(e)}",
                "help": "Contact support if this persists."
            }
        )

    # 2. Run Evaluators
    violations = []
    for evaluator in ACTIVE_EVALUATORS:
        v_list = evaluator.evaluate(graph)
        violations.extend(v_list)

    # 3. Generate DFR (computes hash)
    # Note: generate_dfr handles canonicalization internally for hashing
    dfr = generate_dfr(plan, violations)
    dfr.engine_version = str(ENGINE_VERSION) 
    
    # 4. Check Cache (Idempotency) - Read Path
    existing = db.query(ValidationResult).filter(
        ValidationResult.plan_hash == dfr.plan_hash,
        ValidationResult.engine_version == dfr.engine_version
    ).first()
    
    if existing:
        # Cache Hit
        background_tasks.add_task(create_audit_log, db, current_user.id, request_id, "cache_hit", len(json.loads(existing.dfr_json)))
        
        return DFR(
            plan_hash=existing.plan_hash,
            engine_version=existing.engine_version,
            passed=existing.passed,
            violations=json.loads(existing.dfr_json),
            timestamp=existing.created_at
        )

    # 5. Persist Result - Write Path (Idempotent)
    try:
        # Canonical store
        canonical_plan = canonicalize_json(plan.model_dump())
        violations_json = json.dumps(dfr.violations)
        
        result_record = ValidationResult(
            user_id=current_user.id,
            plan_hash=dfr.plan_hash,
            engine_version=dfr.engine_version,
            schema_version=plan.schema_version, # Lifecycle tracking
            canonical_plan_json=canonical_plan,
            dfr_json=violations_json,
            passed=dfr.passed
        )
        db.add(result_record)
        
        # Add Audit Log in same transaction? 
        # Ideally yes, but if audit fails we might loose validation result?
        # Let's do it in same transaction for strict consistency of "event happened".
        audit = AuditLog(
            request_id=request_id,
            user_id=current_user.id,
            action="validate_plan",
            action_type="validation",
            status="success" if dfr.passed else "failure",
            violations_count=len(dfr.violations)
        )
        db.add(audit)
        
        db.commit()
        
    except IntegrityError:
        # Race condition: another request saved it just now
        db.rollback()
        
        # Retry read
        existing = db.query(ValidationResult).filter(
            ValidationResult.plan_hash == dfr.plan_hash,
            ValidationResult.engine_version == dfr.engine_version
        ).first()
        
        if existing:
             # Log cache hit for this race loser
            background_tasks.add_task(create_audit_log, db, current_user.id, request_id, "cache_hit_race", len(json.loads(existing.dfr_json)))
            
            return DFR(
                plan_hash=existing.plan_hash,
                engine_version=existing.engine_version,
                passed=existing.passed,
                violations=json.loads(existing.dfr_json),
                timestamp=existing.created_at
            )
        else:
            # Should not happen if IntegrityError was due to unique constraint on these fields
            raise HTTPException(status_code=500, detail="Database Integrity Error: Concurrent write failed but read miss.")
            
    return dfr

@router.get("/stats")
def get_validation_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get validation statistics for the dashboard.
    """
    # 1. Counts
    total = db.query(ValidationResult).filter(ValidationResult.user_id == current_user.id).count()
    passed = db.query(ValidationResult).filter(ValidationResult.user_id == current_user.id, ValidationResult.passed == True).count()
    failed = total - passed
    
    # 2. Recent
    recent_objs = db.query(ValidationResult).filter(
        ValidationResult.user_id == current_user.id
    ).order_by(ValidationResult.created_at.desc()).limit(5).all()
    
    recent = []
    for r in recent_objs:
        recent.append({
            "id": str(r.id),
            "plan_hash": r.plan_hash[:8], # Short hash
            "status": "passed" if r.passed else "failed",
            "time": r.created_at.isoformat()
        })
        
    # 3. Top Violations (Scan last 50 failed for MVP)
    # In prod, use a materialized view or proper OLAP
    failed_objs = db.query(ValidationResult).filter(
        ValidationResult.user_id == current_user.id, 
        ValidationResult.passed == False
    ).order_by(ValidationResult.created_at.desc()).limit(50).all()
    
    rule_counts = {}
    for r in failed_objs:
        try:
            dfr = json.loads(r.dfr_json)
            for v in dfr:
                rid = v.get("rule_id", "UNKNOWN")
                rule_counts[rid] = rule_counts.get(rid, 0) + 1
        except:
            pass
            
    # Sort by count desc
    sorted_rules = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_violations = [{"rule": k, "count": v} for k, v in sorted_rules]
    
    return {
        "totalValidations": total,
        "passed": passed,
        "failed": failed,
        "recentValidations": recent,
        "ruleFrequency": top_violations
    }

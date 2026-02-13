
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.db.models import AIRateLimitTracker
from datetime import datetime, timedelta
import uuid

# ── Model Configurations ──
# Only 2 models: Gemini 3 Pro (primary) and Gemini 2.5 Pro (fallback)
MODELS = {
    "gemini-3-flash": {
        "api_name": "gemini-3-flash-preview",
        "display_name": "Gemini 3 Flash",
        "rpm_limit": 15,
        "rpd_limit": 1500,
    },
    "gemini-2.5-flash": {
        "api_name": "gemini-2.5-flash",
        "display_name": "Gemini 2.5 Flash",
        "rpm_limit": 15,
        "rpd_limit": 1500,
    },
}

PRIMARY_MODEL = "gemini-3-flash"
FALLBACK_MODEL = "gemini-2.5-flash"

# Default limits (used when model not found in MODELS)
RPM_LIMIT = 15
RPD_LIMIT = 1500


def get_model_limits(model_id: str) -> tuple[int, int]:
    """Get RPM and RPD limits for a model."""
    cfg = MODELS.get(model_id, {})
    return cfg.get("rpm_limit", RPM_LIMIT), cfg.get("rpd_limit", RPD_LIMIT)


def check_rate_limit(db: Session, user_id: uuid.UUID, model_id: str = PRIMARY_MODEL):
    """
    Enforce Rate Limits (RPM, RPD) using Database.
    Supports per-model limits for Gemini 3 Pro and Gemini 2.5 Pro.

    Returns dict with remaining counts for response headers.
    """
    rpm_limit, rpd_limit = get_model_limits(model_id)
    now = datetime.utcnow()

    # 1. Fetch or Create Tracker
    tracker = db.query(AIRateLimitTracker).filter(
        AIRateLimitTracker.user_id == user_id,
        AIRateLimitTracker.model_id == model_id
    ).with_for_update().first()

    if not tracker:
        tracker = AIRateLimitTracker(
            user_id=user_id,
            model_id=model_id,
            rpm_count=0,
            rpd_count=0,
            last_request_at=now,
            daily_reset_at=now + timedelta(days=1)
        )
        db.add(tracker)

    # 2. Reset Counters if windows expired
    if now - tracker.last_request_at > timedelta(minutes=1):
        tracker.rpm_count = 0

    if now >= tracker.daily_reset_at:
        tracker.rpd_count = 0
        tracker.daily_reset_at = now + timedelta(days=1)

    # 3. Calculate remaining BEFORE incrementing
    rpm_remaining = max(0, rpm_limit - tracker.rpm_count)
    rpd_remaining = max(0, rpd_limit - tracker.rpd_count)

    # 4. Enforce Limits
    if tracker.rpm_count >= rpm_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "type": "rate_limit_exceeded",
                "message": f"Rate limit exceeded ({rpm_limit} requests/minute). Wait 60 seconds.",
                "retry_after_seconds": 60,
                "rpm_limit": rpm_limit,
                "rpd_limit": rpd_limit,
                "model": model_id
            }
        )

    if tracker.rpd_count >= rpd_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "type": "daily_quota_exceeded",
                "message": f"Daily quota reached ({rpd_limit} requests/day). Resets at {tracker.daily_reset_at.isoformat()}Z.",
                "rpd_limit": rpd_limit,
                "resets_at": tracker.daily_reset_at.isoformat(),
                "model": model_id
            }
        )

    # 5. Increment
    tracker.rpm_count += 1
    tracker.rpd_count += 1
    tracker.last_request_at = now

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Rate limiter error")

    return {
        "rpm_remaining": rpm_limit - tracker.rpm_count,
        "rpd_remaining": rpd_limit - tracker.rpd_count,
        "rpm_limit": rpm_limit,
        "rpd_limit": rpd_limit,
        "model": model_id
    }


# Aliases for agent.py compatibility
def check_ai_rate_limit(db: Session, user_id: uuid.UUID, model_id: str = PRIMARY_MODEL):
    """Alias for check_rate_limit — used by agent routes."""
    return check_rate_limit(db, user_id, model_id)


def record_ai_request(db: Session, user_id: uuid.UUID, model_id: str = PRIMARY_MODEL, tokens_used: int = 0):
    """No-op: check_rate_limit already handles increment."""
    pass

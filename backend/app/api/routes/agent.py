
"""
Agent Routes for AI-powered suggestions.

Uses Gemini 3 Pro (primary) with Gemini 2.5 Pro (auto-fallback).
- Key provided per-request in X-Gemini-Key header
- Key is NEVER stored or logged server-side
- Rate limited: 15 RPM, 1500 RPD per model
- Auto-switches to fallback on quota/availability errors
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Header, Response
from sqlalchemy.orm import Session
from typing import Optional
import json
import uuid
import logging

from app.api.routes.auth import get_current_user, get_db
from app.db.models import User, AuditLog, AISuggestion as AISuggestionModel
from app.db.schemas import AISuggestionRequest, AISuggestionResponse, PlanPatchSchema
from app.core.rate_limiter import (
    check_ai_rate_limit, record_ai_request,
    MODELS, PRIMARY_MODEL, FALLBACK_MODEL
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Built-in Prompt ──
BUILTIN_PROMPT = """You are a strict architectural governance assistant. Given a Deterministic Failure Report (DFR) containing architectural violations, suggest structured fixes.

Each fix MUST be a JSON object with these exact fields:
- "operation": one of "add", "remove", or "modify"
- "type": one of "component", "resource", "relationship", or "env_var"
- "target_path": the path in the plan schema (e.g., "components.backend.resources.api_users")
- "method": HTTP method if applicable (e.g., "POST", "GET"), or null
- "details": object with additional context
- "confidence": one of "high", "medium", or "low"

DFR:
{dfr_json}

Return ONLY a valid JSON array of fix objects. No markdown fences. No explanations. Just the JSON array."""


def _call_gemini(api_key: str, prompt: str, model_id: str = PRIMARY_MODEL) -> list[dict]:
    """
    Call a Gemini model with the user's BYOK key.
    Returns parsed list of suggestion dicts.
    """
    import google.generativeai as genai

    # Get API model name from config
    model_cfg = MODELS.get(model_id, MODELS[PRIMARY_MODEL])
    api_model_name = model_cfg["api_name"]

    # Configure with user's key (per-request, not stored)
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(api_model_name)

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.1,  # Low temp for deterministic structured output
            "max_output_tokens": 4096,
        }
    )

    raw_text = response.text.strip()

    # Strip markdown fences if the model wraps output
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw_text = "\n".join(lines)

    parsed = json.loads(raw_text)

    if not isinstance(parsed, list):
        parsed = [parsed]

    return parsed


def _call_with_fallback(api_key: str, prompt: str) -> tuple[list[dict], str]:
    """
    Try Gemini 3 Pro first. If it fails with quota/availability errors,
    auto-switch to Gemini 2.5 Pro.

    Returns (suggestions, model_id_used).
    """
    try:
        logger.info(f"Calling primary model: {MODELS[PRIMARY_MODEL]['display_name']}")
        result = _call_gemini(api_key, prompt, PRIMARY_MODEL)
        return result, PRIMARY_MODEL

    except Exception as primary_error:
        error_msg = str(primary_error)
        is_quota_or_availability = any(kw in error_msg for kw in [
            "RESOURCE_EXHAUSTED", "quota", "429",
            "not found", "404", "not supported",
            "temporarily unavailable", "503"
        ])

        if not is_quota_or_availability:
            # Not a fallback-able error — re-raise as-is
            raise

        logger.warning(
            f"Primary model ({MODELS[PRIMARY_MODEL]['display_name']}) unavailable: "
            f"{error_msg[:100]}. Falling back to {MODELS[FALLBACK_MODEL]['display_name']}."
        )

        try:
            result = _call_gemini(api_key, prompt, FALLBACK_MODEL)
            return result, FALLBACK_MODEL

        except Exception as fallback_error:
            fallback_msg = str(fallback_error)
            logger.error(
                f"Fallback model ({MODELS[FALLBACK_MODEL]['display_name']}) also failed: "
                f"{fallback_msg[:100]}"
            )
            # Classify and raise the fallback error
            _raise_gemini_error(fallback_msg, fallback_model=True)


def _raise_gemini_error(error_msg: str, fallback_model: bool = False):
    """Classify a Gemini error and raise the appropriate HTTPException."""
    model_label = "Both Gemini 3 Pro and 2.5 Pro" if fallback_model else "Gemini"

    if "API_KEY_INVALID" in error_msg or "API key not valid" in error_msg:
        raise HTTPException(
            status_code=403,
            detail={
                "type": "invalid_api_key",
                "message": "Your Gemini API key is invalid. Check your key in Settings.",
                "help": "Get a valid key from https://aistudio.google.com/apikey"
            }
        )
    elif "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
        raise HTTPException(
            status_code=429,
            detail={
                "type": "gemini_quota_exceeded",
                "message": f"{model_label} quota exhausted. Wait and try again.",
            }
        )
    elif "SAFETY" in error_msg:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "safety_filter",
                "message": "Gemini safety filters blocked this request. Try a different plan.",
            }
        )
    else:
        raise HTTPException(
            status_code=502,
            detail={
                "type": "ai_provider_error",
                "message": f"Gemini API error: {error_msg[:200]}",
            }
        )


@router.post("/suggest", response_model=list[AISuggestionResponse])
async def suggest_fixes(
    request: AISuggestionRequest,
    response: Response,
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-powered fix suggestions for a DFR.

    BYOK key must be provided via X-Gemini-Key header.
    Key is NOT stored or logged.

    Primary: Gemini 3 Pro (15 RPM, 1500 RPD)
    Fallback: Gemini 2.5 Pro (15 RPM, 1500 RPD)
    Auto-switches on quota/availability errors.
    """
    # 1. Check BYOK key
    if not x_gemini_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "byok_required",
                "message": "API key required. Provide your Gemini key in the X-Gemini-Key header.",
                "help": "Go to Settings → AI Provider and enter your Gemini API key."
            }
        )

    # 2. Rate Limit Check (checks primary model limit)
    rate_info = check_ai_rate_limit(db, current_user.id, PRIMARY_MODEL)

    # Add rate limit headers
    response.headers["X-RateLimit-RPM-Remaining"] = str(rate_info["rpm_remaining"])
    response.headers["X-RateLimit-RPD-Remaining"] = str(rate_info["rpd_remaining"])
    response.headers["X-RateLimit-RPM-Limit"] = str(rate_info["rpm_limit"])
    response.headers["X-RateLimit-RPD-Limit"] = str(rate_info["rpd_limit"])
    response.headers["X-RateLimit-Model"] = rate_info["model"]

    # 3. Build prompt
    if request.prompt_mode == "builtin":
        prompt = BUILTIN_PROMPT.format(dfr_json=json.dumps(request.dfr_json, indent=2))
    else:
        if not request.custom_prompt:
            raise HTTPException(status_code=400, detail="custom_prompt required when prompt_mode is 'custom'")
        prompt = request.custom_prompt + f"\n\nDFR:\n{json.dumps(request.dfr_json, indent=2)}"

    # 4. Call Gemini with auto-fallback
    try:
        raw_suggestions, model_used = _call_with_fallback(x_gemini_key, prompt)
    except HTTPException:
        raise  # Already classified
    except json.JSONDecodeError as e:
        logger.warning(f"Gemini returned non-JSON: {e}")
        raise HTTPException(
            status_code=502,
            detail={
                "type": "ai_parse_error",
                "message": "Gemini returned invalid JSON. Try again.",
            }
        )
    except Exception as e:
        _raise_gemini_error(str(e))

    # Add which model actually served the response
    model_cfg = MODELS.get(model_used, MODELS[PRIMARY_MODEL])
    response.headers["X-AI-Model"] = model_cfg["display_name"]
    if model_used != PRIMARY_MODEL:
        response.headers["X-AI-Fallback"] = "true"

    # 5. Parse into structured responses
    suggestions = []
    violations = request.dfr_json.get("violations", [])
    violation_ids = [v.get("id", f"v_{i}") for i, v in enumerate(violations)]

    for i, raw in enumerate(raw_suggestions):
        try:
            patch = PlanPatchSchema(
                operation=raw.get("operation", "modify"),
                type=raw.get("type", "resource"),
                target_path=raw.get("target_path", "unknown"),
                method=raw.get("method"),
                details=raw.get("details", {}),
                confidence=raw.get("confidence", "medium")
            )

            violation_id = violation_ids[i] if i < len(violation_ids) else f"suggestion_{i}"

            suggestions.append(AISuggestionResponse(
                violation_id=violation_id,
                suggestion=raw.get("details", {}).get("description", f"Fix: {raw.get('operation', 'modify')} {raw.get('type', 'resource')} at {raw.get('target_path', 'unknown')}"),
                confidence=raw.get("confidence", "medium"),
                patches=[patch]
            ))
        except Exception as e:
            logger.warning(f"Failed to parse suggestion {i}: {e}")
            continue

    # 6. Persist suggestions
    suggestion_record = AISuggestionModel(
        user_id=current_user.id,
        plan_hash=request.plan_hash,
        engine_version=request.engine_version,
        suggestion_json=json.dumps([s.model_dump() for s in suggestions]),
        prompt_mode=request.prompt_mode
    )
    db.add(suggestion_record)

    # Audit log
    audit = AuditLog(
        request_id=uuid.uuid4(),
        user_id=current_user.id,
        action="ai_suggest",
        action_type="ai_suggestion",
        status="success",
        violations_count=len(violations)
    )
    db.add(audit)

    db.commit()

    return suggestions


@router.get("/suggestions")
async def get_suggestions(
    plan_hash: str,
    engine_version: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Query stored AI suggestions by plan_hash.
    Optionally filter by engine_version to avoid stale suggestions.
    """
    query = db.query(AISuggestionModel).filter(
        AISuggestionModel.user_id == current_user.id,
        AISuggestionModel.plan_hash == plan_hash
    )

    if engine_version:
        query = query.filter(AISuggestionModel.engine_version == engine_version)

    records = query.order_by(AISuggestionModel.created_at.desc()).all()

    return [
        {
            "id": str(r.id),
            "plan_hash": r.plan_hash,
            "engine_version": r.engine_version,
            "suggestions": json.loads(r.suggestion_json),
            "prompt_mode": r.prompt_mode,
            "created_at": r.created_at.isoformat()
        }
        for r in records
    ]

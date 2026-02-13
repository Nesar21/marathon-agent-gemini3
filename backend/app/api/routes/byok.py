
"""
BYOK Routes.

CRITICAL: Persistent BYOK storage is DISABLED.
All key storage must be client-side (sessionStorage) only.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.routes.auth import get_current_user, get_db
from app.db.models import User

router = APIRouter()


@router.post("/save")
def save_api_key(current_user: User = Depends(get_current_user)):
    """
    DISABLED: Persistent BYOK storage.
    Keys must be stored in client sessionStorage only.
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "type": "byok_storage_disabled",
            "message": "Persistent key storage is disabled. Store your API key in your browser session only.",
            "help": "Your key is cached locally for this tab session. It will be cleared when you close the tab."
        }
    )


@router.get("/status")
def get_api_key_status(current_user: User = Depends(get_current_user)):
    """
    Returns status of BYOK. Since persistent storage is disabled, 
    this always returns that no keys are stored server-side.
    """
    return {
        "persistent_storage_enabled": False,
        "stored_keys_count": 0,
        "message": "Keys are stored in your browser session only (sessionStorage). Not on server."
    }


@router.delete("/remove/{key_id}")
def remove_api_key(key_id: str, current_user: User = Depends(get_current_user)):
    """
    DISABLED: No keys to remove since nothing is stored.
    """
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No server-stored keys to remove. Keys are session-only."
    )

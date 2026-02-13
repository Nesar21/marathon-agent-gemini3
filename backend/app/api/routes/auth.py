# STATUS: FROZEN
# STRICT MODE: DO NOT EDIT WITHOUT EXPLICIT APPROVAL
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core import security
from app.api import deps
from app.core.config import settings
from app.db.models import User
from app.db.schemas import Token, UserCreate, UserResponse, PasswordResetRequest

# Re-export key dependencies for compatibility with other modules (byok.py, validation.py)
from app.api.deps import get_current_user, get_db

router = APIRouter()

class UserSignupResponse(UserResponse):
    recovery_key: str

@router.post("/signup", response_model=UserSignupResponse)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Create new user.
    """
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    # Generate Recovery Key
    import uuid
    recovery_key_raw = str(uuid.uuid4())
    # Encrypt recovery key
    encrypted_recovery_key = security.encrypt_value(recovery_key_raw)

    user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        is_active=True, # Auto-activate for ease
        recovery_key=encrypted_recovery_key
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Return user data + raw recovery key
    return UserSignupResponse(
        id=user.id,
        email=user.email,
        plan_tier=user.plan_tier,
        created_at=user.created_at,
        recovery_key=recovery_key_raw
    )

@router.post("/token", response_model=Token)
def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.get("/me", response_model=UserResponse)
def read_users_me(
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get current user.
    """
    return current_user

@router.get("/recovery-key")
def get_recovery_key(
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get decrypted recovery key.
    """
    if not current_user.recovery_key:
        raise HTTPException(status_code=404, detail="No recovery key set")
    
    key = security.decrypt_value(current_user.recovery_key)
    if not key:
        # Fallback if key was hashed or corrupted
        raise HTTPException(status_code=500, detail="Could not decrypt recovery key")
        
    return {"recovery_key": key}

@router.post("/reset-password")
def reset_password(
    payload: PasswordResetRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Reset password using recovery key.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.recovery_key:
         raise HTTPException(status_code=400, detail="No recovery key set for this user")
         
    # Try decrypt first (New Flow)
    stored_key = security.decrypt_value(user.recovery_key)
    if stored_key:
        if stored_key != payload.recovery_key:
            raise HTTPException(status_code=400, detail="Invalid recovery key")
    else:
        # Fallback to verify hash (Old Flow / Legacy Users)
        if not security.verify_password(payload.recovery_key, user.recovery_key):
            raise HTTPException(status_code=400, detail="Invalid recovery key")
        
    user.hashed_password = security.get_password_hash(payload.new_password)
    
    db.add(user)
    db.commit()
    
    return {"message": "Password updated successfully"}

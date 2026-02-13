
from datetime import datetime
import uuid
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base
from typing import Any

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    plan_tier: Mapped[str] = mapped_column(String, default="free")  # 'free', 'pro', 'enterprise'
    
    # Email verification fields
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verification_token: Mapped[str] = mapped_column(String(64), nullable=True)
    
    # Recovery Key (Encrypted)
    recovery_key: Mapped[str] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    validation_results = relationship("ValidationResult", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    rate_limits = relationship("AIRateLimitTracker", back_populates="user")
    ai_suggestions = relationship("AISuggestion", back_populates="user")

class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # Encrypted data stored as JSON string or composite columns
    # We store the JSON structure {ciphertext, iv, salt} as a Text field for SQLite compatibility/Simplicity
    # In a real PG setup, this could be JSONB, but Text works for both.
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False) 
    
    key_hash: Mapped[str] = mapped_column(String, index=True, nullable=False)  # SHA256 for lookup
    provider: Mapped[str] = mapped_column(String, default="gemini_cloud")
    model_id: Mapped[str] = mapped_column(String, default="gemini-3-flash")
    is_active: Mapped[str] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="api_keys")

class ValidationResult(Base):
    __tablename__ = "validation_result"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    plan_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    # Lifecycle: Store schema version to know how to validate/migrate old plans
    schema_version: Mapped[str] = mapped_column(String(16), default="1.0", nullable=False)
    
    # Store JSONs. Use Text for SQLite/Generic compatibility, cast to JSONB in PG if needed.
    canonical_plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    dfr_json: Mapped[str] = mapped_column(Text, nullable=False)
    
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="validation_results")

    __table_args__ = (
        # Idempotency constraint
        UniqueConstraint('plan_hash', 'engine_version', name='uq_plan_engine_version'),
    )

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    action: Mapped[str] = mapped_column(String, nullable=False) # e.g., "validate_plan"
    action_type: Mapped[str] = mapped_column(String, nullable=False) # "validation", "ai_suggestion"
    status: Mapped[str] = mapped_column(String, nullable=False) # "success", "failure", "cache_hit"
    violations_count: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="audit_logs")

class AIRateLimitTracker(Base):
    __tablename__ = "ai_rate_limit_tracker"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    model_id: Mapped[str] = mapped_column(String, nullable=False)
    
    rpm_count: Mapped[int] = mapped_column(Integer, default=0)
    rpd_count: Mapped[int] = mapped_column(Integer, default=0)
    
    last_request_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    daily_reset_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="rate_limits")

class AISuggestion(Base):
    """
    Stores structured AI suggestions associated with a DFR.
    These are the ONLY AI outputs stored. They do NOT alter canonical_plan_json.
    """
    __tablename__ = "ai_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    plan_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Structured suggestions as JSON: List[PlanPatchSchema]
    suggestion_json: Mapped[str] = mapped_column(Text, nullable=False)
    
    prompt_mode: Mapped[str] = mapped_column(String(16), default="builtin") # "builtin" | "custom"
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="ai_suggestions")


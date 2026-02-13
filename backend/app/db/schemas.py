
from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field, AnyHttpUrl, validator, constr
from datetime import datetime
import uuid

# --- Plan Schema Models ---

class Resource(BaseModel):
    id: str
    type: str # 'api', 'table', 'migration', 'topic', 'job'
    name: str
    description: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    
class Component(BaseModel):
    id: str
    name: str
    type: Literal['frontend', 'backend', 'database', 'worker', 'cli']
    path: str
    resources: List[Resource] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list) # Component IDs

class Relationship(BaseModel):
    source: str # Component ID or Resource ID
    target: str # Component ID or Resource ID
    type: Literal['calls', 'creates', 'reads', 'updates', 'deletes', 'depends_on']
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PlanSchema(BaseModel):
    schema_version: str = Field(..., description="Version of the schema, e.g. '1.0'")
    project_name: str
    components: List[Component]
    relationships: List[Relationship]
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Env vars with masked values or references")
    
    model_config = {
        "extra": "forbid"
    }

# --- API Models ---

class DFR(BaseModel):
    plan_hash: str
    engine_version: str
    passed: bool
    violations: List[Dict[str, Any]]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PlanPatchSchema(BaseModel):
    """Structured patch schema for AI suggestions. Must not be free-text."""
    operation: Literal['add', 'remove', 'modify']
    type: Literal['component', 'resource', 'relationship', 'env_var']
    target_path: str  # e.g., "components.backend.resources.api_users"
    method: Optional[str] = None  # e.g., "POST", "GET" for APIs
    details: Dict[str, Any] = Field(default_factory=dict)
    confidence: Literal['high', 'medium', 'low'] = 'medium'

class AISuggestionRequest(BaseModel):
    """Request body for /api/agent/suggest"""
    plan_hash: str
    engine_version: str
    dfr_json: Dict[str, Any]
    prompt_mode: Literal['builtin', 'custom'] = 'builtin'
    custom_prompt: Optional[str] = None

class AISuggestionResponse(BaseModel):
    """Response from /api/agent/suggest"""
    violation_id: str
    suggestion: str
    confidence: Literal['high', 'medium', 'low']
    patches: List[PlanPatchSchema] = Field(default_factory=list)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    sub: Optional[str] = None

    model_config = {"extra": "allow"}

class UserCreate(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    plan_tier: str
    created_at: datetime
    is_active: bool = True

class APIKeyCreate(BaseModel):
    provider: str = "gemini_cloud"
    model_id: str = "gemini-3-flash"
    # The actual key is sent in a specific endpoint or header, 
    # but for creation payload we might handle it separately or here.
    # For BYOK flow, we usually send the key in the body to /byok/save
    api_key: str 

class APIKeyResponse(BaseModel):
    id: uuid.UUID
    provider: str
    model_id: str
    is_active: bool
    created_at: datetime
    # key_hash: str # Optional to show

class PasswordResetRequest(BaseModel):
    email: str
    recovery_key: str
    new_password: str

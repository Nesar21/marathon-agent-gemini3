
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import uuid
import logging
import json
import time

from app.core.config import settings

# Database Setup - MUST be before route imports to avoid circular imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import models and create tables
from app.db.models import Base
Base.metadata.create_all(bind=engine)

# NOW import routes (after SessionLocal is defined)
from app.api.routes import auth, byok, validation, agent, health
from app.core.metrics import PrometheusMiddleware, metrics_endpoint

# Setup structured logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("governance_engine")

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

class LogRedactionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Redact sensitive headers from logs
        # Note: starlette Request object is immutable for headers in some contexts, 
        # so we primarily focus on preventing the logger from seeing it, 
        # or ensuring our own logs don't dump headers.
        # This middleware ensures we strip it from the scope if we were doing deep debug logging.
        
        # We can't easily modify the incoming request headers before they hit the endpoint 
        # without breaking signatures, but we can ensure our ACCESS LOGS don't show them.
        # Standard uvicorn logs don't show headers by default.
        # We will add a structured log entry here that explicitly EXCLUDES the key.
        
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        log_exclude = {"x-gemini-key", "authorization"}
        safe_headers = {k: v for k, v in request.headers.items() if k.lower() not in log_exclude}
        
        log_entry = {
            "timestamp": time.time(),
            "request_id": getattr(request.state, "request_id", None),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration": process_time,
            "ip": getattr(request.client, "host", "unknown") if request.client else "unknown",
            "user_agent": request.headers.get("user-agent"),
            # "headers": safe_headers # Uncomment if we need header debugging
        }
        
        # Structured Log
        print(json.dumps(log_entry))
        
        return response

app = FastAPI(
    title=settings.PROJECT_NAME, 
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS - Must be FIRST to wrap all responses properly
# In Starlette, middleware added first executes last (wraps everything)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-AI-Model", "X-AI-Fallback",
        "X-RateLimit-RPM-Remaining", "X-RateLimit-RPD-Remaining",
        "X-RateLimit-RPM-Limit", "X-RateLimit-RPD-Limit", "X-RateLimit-Model"
    ],
)

# Other middleware after CORS
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LogRedactionMiddleware)
app.add_middleware(PrometheusMiddleware)

app.add_route("/metrics", metrics_endpoint)

@app.get("/health/live")
def health_live():
    return {"status": "alive"}

@app.get("/health/ready")
def health_ready():
    # In a real app, check DB connection here
    return {"status": "ready"}

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(byok.router, prefix="/api/byok", tags=["byok"])
app.include_router(validation.router, prefix="/api/validate", tags=["validation"])
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])

@app.api_route("/", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
@app.api_route("/api", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
@app.api_route("/.netlify/functions/api", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def catch_all(request: Request, path_name: str = ""):
    return {
        "detail": f"Debug: received_path={path_name}, method={request.method}, base_url={request.base_url}, url={request.url}"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()

@router.get("/live")
def health_live():
    return {"status": "alive"}

@router.get("/ready")
def health_ready():
    return {"status": "ready"}

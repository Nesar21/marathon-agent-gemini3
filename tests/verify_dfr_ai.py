
import sys
import os
import requests
import json
import uuid

# Add backend to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from app.main import SessionLocal
from app.db.models import User
from app.core.config import settings

# Configuration
API_URL = "http://localhost:8000/api"
EMAIL = "ai_verification@example.com"
PASSWORD = "AiTestPassword123!"

def setup_user():
    print(f"[*] Setting up user {EMAIL}...")
    db = SessionLocal()
    try:
        # Check if user exists
        user = db.query(User).filter(User.email == EMAIL).first()
        if not user:
            print("    Creating new user via API (to trigger hashing)...")
            try:
                resp = requests.post(f"{API_URL}/auth/signup", json={
                    "email": EMAIL,
                    "password": PASSWORD
                })
                if resp.status_code == 201:
                    print("    User created via API.")
                else:
                    print(f"    Failed to create user via API: {resp.text}")
                    # Might rely on DB creation if API fails, but let's try to assume success or exist
            except Exception as e:
                print(f"    API Error: {e}")

        # Refresh user from DB
        user = db.query(User).filter(User.email == EMAIL).first()
        if user:
            if not user.is_active:
                print("    Activating user in DB...")
                user.is_active = True
                db.commit()
            else:
                print("    User already active.")
        else:
            print("    ERROR: User could not be created/found.")
            sys.exit(1)
            
    finally:
        db.close()

def login():
    print("[*] Logging in...")
    resp = requests.post(f"{API_URL}/auth/token", data={
        "username": EMAIL,
        "password": PASSWORD
    })
    if resp.status_code != 200:
        print(f"    Login Failed: {resp.text}")
        sys.exit(1)
    
    token = resp.json()["access_token"]
    print("    Login Successful.")
    return token

def test_dfr_ai(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Gemini-Key": "dummy_key_for_mock_ai" 
    }
    
    # 1. Trigger DB_MIG_001 (Table without migration)
    print("\n[*] Test 1: Triggering DFR Violation (DB_MIG_001)...")
    plan = {
        "schema_version": "1.0",
        "project_name": "AI Verification Plan",
        "components": [
            {
                "id": "database",
                "name": "Main Database",
                "type": "database",
                "path": "/data",
                "resources": [
                    {
                        "id": "users_table",
                        "name": "Users Table",
                        "type": "table",
                        "properties": {
                            "columns": ["id", "email"]
                        }
                    }
                ],
                "dependencies": []
            }
        ],
        "relationships": [],
        "env_vars": {}
    }
    
    resp = requests.post(f"{API_URL}/validate", json=plan, headers=headers)
    if resp.status_code != 200:
        print(f"    Validation Failed: {resp.status_code} {resp.text}")
        sys.exit(1)
        
    dfr = resp.json()
    violations = dfr.get("violations", [])
    print(f"    DFR Generated. Violations count: {len(violations)}")
    
    # Check for DB_MIG_001
    mig_violations = [v for v in violations if v.get("rule_id") == "DB_MIG_001"]
    if not mig_violations:
        print("    ERROR: Expected DB_MIG_001 violation not found!")
        print(f"    Actual violations: {json.dumps(violations, indent=2)}")
        sys.exit(1)
    else:
        print("    SUCCESS: Caught DB_MIG_001 (Missing Migration).")
        
    # 2. Request AI Suggestions
    print("\n[*] Test 2: Requesting AI Suggestions...")
    
    # We pass the DFR we just got
    ai_request = {
        "plan_hash": dfr["plan_hash"],
        "engine_version": dfr["engine_version"],
        "dfr_json": dfr,
        "prompt_mode": "builtin"
    }
    
    resp = requests.post(f"{API_URL}/agent/suggest", json=ai_request, headers=headers)
    if resp.status_code != 200:
        print(f"    AI Request Failed: {resp.status_code} {resp.text}")
        sys.exit(1)
        
    suggestions = resp.json()
    print(f"    AI Suggestions Received: {len(suggestions)}")
    
    # Check content
    print(f"    Suggestion Content: {json.dumps(suggestions, indent=2)}")
    
    if len(suggestions) > 0 and "Create migration file" in str(suggestions):
        print("\n[SUCCESS] AI Suggestion logic is working correctly (Mocked).")
    else:
        print("\n[FAILURE] AI Suggestion did not return expected fix.")

if __name__ == "__main__":
    setup_user()
    token = login()
    test_dfr_ai(token)

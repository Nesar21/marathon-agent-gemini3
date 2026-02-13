import requests
import json
import uuid
import time
import sys

BASE_URL = "http://localhost:8000/api"
EMAIL = "test_user_premium@example.com" 
PASSWORD = "password123"

def login():
    try:
        # Login uses /token endpoint (OAuth2 standard)
        response = requests.post(f"{BASE_URL}/auth/token", data={"username": EMAIL, "password": PASSWORD})
        if response.status_code == 200:
            return response.json()["access_token"]
            
        print(f"Login failed ({response.status_code}), attempting signup...")
        signup_email = f"hardcore_{uuid.uuid4().hex[:6]}@test.com"
        resp = requests.post(f"{BASE_URL}/auth/signup", json={"email": signup_email, "password": PASSWORD})
        
        if resp.status_code in [200, 201]:
            print(f"Registered {signup_email}")
            login_resp = requests.post(f"{BASE_URL}/auth/token", data={"username": signup_email, "password": PASSWORD})
            return login_resp.json()["access_token"]
        else:
            print(f"Signup failed: {resp.text}")
            sys.exit(1)
    except Exception as e:
        print(f"Connection error: {e}")
        sys.exit(1)

TOKEN = login()
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def run_test(name, payload, expected_status=200, expected_error_type=None, check_passed=None, description=""):
    print(f"\n--- Test: {name} ---")
    print(f"Goal: {description}")
    
    start = time.time()
    try:
        response = requests.post(f"{BASE_URL}/validate", json=payload, headers=HEADERS)
        duration = time.time() - start
        
        if response.status_code != expected_status:
            print(f"FAILED: Expected status {expected_status}, got {response.status_code}")
            print(f"Response: {response.text}")
            return False

        if expected_error_type:
            data = response.json()
            detail = data.get("detail", {})
            actual_type = detail.get("type", "unknown") if isinstance(detail, dict) else "string"
            if actual_type != expected_error_type:
                print(f"FAILED: Expected error type '{expected_error_type}', got '{actual_type}'")
                print(f"Detail: {detail}")
                return False

        if check_passed is not None:
            data = response.json()
            if data.get("passed") != check_passed:
                print(f"FAILED: Expected passed={check_passed}, got {data.get('passed')}")
                print(f"Violations: {json.dumps(data.get('violations'), indent=2)}")
                return False

        print(f"PASSED ({duration:.3f}s)")
        return True
        
    except Exception as e:
        print(f"CRITICAL FAILURE: {e}")
        return False

# --- Payloads ---

def basic_plan():
    return {
        "schema_version": "1.0",
        "project_name": "Hardcore Test",
        "components": [
            {"id": "web", "type": "frontend", "name": "Web", "path": "/web", "resources": []},
            {"id": "api", "type": "backend", "name": "API", "path": "/api", "resources": [
                {"id": "users_ep", "type": "api", "name": "Get Users", "properties": {"method": "GET", "path": "/users"}}
            ]}
        ],
        "relationships": [
            {"source": "web", "target": "api", "type": "calls", "metadata": {"path": "/users", "method": "GET"}}
        ]
    }

results = []

# 1. Valid Plan
results.append(run_test("Valid Plan", basic_plan(), expected_status=200, check_passed=True, description="Simple valid call matching API."))

# 2. Missing Field
bad_schema = basic_plan()
del bad_schema["components"]
results.append(run_test("Missing Components", bad_schema, expected_status=422, description="Missing required field."))

# 3. Invalid Enum
bad_enum = basic_plan()
bad_enum["components"][0]["type"] = "magic"
results.append(run_test("Invalid Enum", bad_enum, expected_status=422, description="Invalid component type."))

# 4. Ambiguous Routes
ambiguous = basic_plan()
ambiguous["components"][1]["resources"].append(
    {"id": "dup", "type": "api", "name": "Dup", "properties": {"method": "GET", "path": "/users"}}
)
results.append(run_test("Ambiguous Routes", ambiguous, expected_status=400, expected_error_type="compilation_error", description="Duplicate API routes."))

# 5. Unresolved Call
unresolved = basic_plan()
unresolved["relationships"][0]["metadata"]["path"] = "/404"
results.append(run_test("Unresolved Call", unresolved, expected_status=400, expected_error_type="compilation_error", description="Call to non-existent path."))

# 6. DB Violation
db_plan = {
    "schema_version": "1.0", "project_name": "DB",
    "components": [{"id": "db", "type": "database", "name": "DB", "path": "/db", "resources": [{"id": "t1", "type": "table", "name": "t1"}]}],
    "relationships": []
}
results.append(run_test("DB Violation", db_plan, expected_status=200, check_passed=False, description="Table without migration."))

# 7. Frontend Mismatch (Evaluator)
mismatch = basic_plan()
# Point directly to the API RESOURCE ID, but give wrong path metadata
# This bypasses the Builder's Component-level path search (which would fail 400)
# So Builder says "Edge to u1 exists", OK.
# Evaluator says "Edge to u1 has path /wrong, u1 has path /users", FAIL.
mismatch["relationships"][0]["target"] = "users_ep" 
mismatch["relationships"][0]["metadata"]["path"] = "/wrong"
results.append(run_test("Metadata Mismatch", mismatch, expected_status=200, check_passed=False, description="Valid edge but wrong metadata path."))

# 8. Large Payload
large = basic_plan()
large["components"].extend([
    {"id": f"w{i}", "type": "worker", "name": f"W{i}", "path": f"/w{i}", "resources": []} 
    for i in range(500)
])
results.append(run_test("Large Payload", large, expected_status=200, check_passed=True, description="500 components stress test."))

# 9. Cycle
cycle = basic_plan()
cycle["relationships"].append({"source": "api", "target": "web", "type": "calls"})
results.append(run_test("Cycle", cycle, expected_status=200, check_passed=True, description="Cyclic dependency is allowed."))

# 10. Empty
empty = {"schema_version": "1.0", "project_name": "E", "components": [], "relationships": []}
results.append(run_test("Empty", empty, expected_status=200, check_passed=True, description="Empty plan is valid."))

print(f"\nFinal: {sum(results)}/{len(results)} Passed")
if not all(results): sys.exit(1)

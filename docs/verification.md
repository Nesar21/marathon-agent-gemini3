
"""
Verification documentation for Governance Engine.

This file contains cURL examples and manual verification steps for all API endpoints.
"""

# ============================================
# AUTHENTICATION
# ============================================

# 1. Sign Up (creates inactive user, sends verification email)
```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"P@ssw0rd!"}'
```
# Expected: 201 Created, message about email verification

# 2. Attempt login before activation (should fail)
```bash
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=P@ssw0rd!"
```
# Expected: 403 Forbidden, "Account not activated"

# 3. Activate account (check console for token in dev mode)
# Note: Now requires email parameter for secure lookup
```bash
curl "http://localhost:8000/api/auth/activate?token=<TOKEN_FROM_EMAIL>&email=test@example.com"
```
# Expected: 200 OK, "Account activated successfully"

# 4. Login with activated account
```bash
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=P@ssw0rd!"
```
# Expected: 200 OK, {"access_token": "...", "token_type": "bearer"}

# ============================================
# VALIDATION
# ============================================

# 5. Validate a plan (requires auth token)
```bash
curl -X POST http://localhost:8000/api/validate/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": "1.0",
    "project_name": "Test Project",
    "components": [
      {"id": "frontend", "name": "Web", "type": "frontend", "path": "/web", "resources": [], "dependencies": ["backend"]},
      {"id": "backend", "name": "API", "type": "backend", "path": "/api", "resources": [], "dependencies": []}
    ],
    "relationships": [],
    "env_vars": {}
  }'
```
# Expected: 200 OK with DFR (plan_hash, engine_version, passed, violations)

# 6. Re-validate same plan (should return cache hit)
```bash
# Run the same command again
# Expected: 200 OK with cache_hit: true (same plan_hash)
```

# ============================================
# AI SUGGESTIONS
# ============================================

# 7. Get AI suggestions (requires BYOK key in header)
```bash
curl -X POST http://localhost:8000/api/agent/suggest \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "X-Gemini-Key: <YOUR_GEMINI_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_hash": "<PLAN_HASH>",
    "engine_version": "<ENGINE_VERSION>",
    "dfr_json": {"violations": [{"rule_id": "FE_BE_001", "offending_node": "/api/users"}]},
    "prompt_mode": "builtin"
  }'
```
# Expected: 200 OK with structured suggestions (PlanPatchSchema)

# 8. Query stored suggestions
```bash
curl http://localhost:8000/api/agent/suggestions?plan_hash=<PLAN_HASH> \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```
# Expected: 200 OK with list of stored suggestions

# ============================================
# BYOK (SESSION-ONLY)
# ============================================

# 9. Attempt to save key server-side (MUST fail)
```bash
curl -X POST http://localhost:8000/api/byok/save \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"api_key": "AIza..."}'
```
# Expected: 403 Forbidden, "Persistent key storage is disabled"

# 10. Check BYOK status
```bash
curl http://localhost:8000/api/byok/status \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```
# Expected: 200 OK, {"persistent_storage_enabled": false, "stored_keys_count": 0}

# ============================================
# MANUAL VERIFICATION CHECKLIST
# ============================================

## Authentication Flow
- [ ] Sign up from UI -> "Check your email" message appears
- [ ] Attempt login before activation -> "Account not activated" error
- [ ] Check console/email for activation link
- [ ] Click activation link -> Success message
- [ ] Login after activation -> Redirected to dashboard

## BYOK Session Storage
- [ ] Enter API key in Settings -> "Key cached for this session only" message
- [ ] Reload page in same tab -> Key still present
- [ ] Open new tab/window -> Key NOT present
- [ ] Check database -> No api_keys rows with the key

## Validation Flow
- [ ] Click "Load Sample" on dashboard -> JSON appears
- [ ] Click "Validate Plan" -> Spinner shows -> DFR appears
- [ ] Re-validate same plan -> "CACHED" indicator shows
- [ ] Check database -> Only ONE validation_result row

## AI Suggestions
- [ ] After failed validation, click "Get AI Suggestions"
- [ ] If no key set -> Error prompts to add key in Settings
- [ ] After adding key -> Structured suggestions appear
- [ ] Suggestions show operation/type/target_path (not free text)

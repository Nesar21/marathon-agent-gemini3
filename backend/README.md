# Governance Engine Backend

Full-stack deterministic architectural governance engine.

## Features

- **Engine Core**: Graph-based architecture validation with ambiguity rejection.
- **BYOK**: Bring Your Own Key (Gemini) with AES-GCM encryption.
- **Idempotency**: Cached validation results based on `plan_hash` + `engine_version`.
- **AI Rate Limiting**: Strict 5 RPM limit for AI suggestions; UNLIMITED for validation.
- **CLI**: Offline validation tool.

## Setup

1. **Install Dependencies**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Initialize Database**:
   ```bash
   # Make sure alembic is installed
   alembic upgrade head
   ```

3. **Run Server**:
   ```bash
   uvicorn app.main:app --reload
   ```

## CLI Usage

Validate a plan without running the server:

```bash
python cli/validate.py test_plan.json
```

## Testing

Run unit tests:

```bash
pytest tests/
```

## API Documentation

Once running, visit `http://localhost:8000/docs`.

### Key Endpoints

- `POST /api/byok/save`: Save encrypted API key.
- `POST /api/validate`: Validate plan (Unlimited).
- `POST /api/agent/suggest`: Get AI suggestions (Rate Limited).

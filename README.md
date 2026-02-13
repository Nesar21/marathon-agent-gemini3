# Governance Engine (MVP)
## Dual Model AI Architecture

![Dashboard](docs/assets/dashboard.png)

A high-performance **Governance Engine** featuring a serverless Python backend (FastAPI) and a modern Next.js 14 frontend. It leverages a **Dual Model AI System** (Gemini 3 Flash + 2.5 Flash Fallback) to provide robust, deterministic analysis of system plans.

## 🚀 Features

- **Dual Model AI**: 
  - **Primary**: Google Gemini 3 Flash (High speed, low cost).
  - **Fallback**: Google Gemini 2.5 Flash (Automatic failover on rate limits/errors).
- **Deterministic Failure Report (DFR) Engine**: 
  - Strictly deterministic analysis of JSON system plans.
  - No AI hallucinations for critical validation rules.
- **BYOK (Bring Your Own Key)**:
  - Users can securely provide their own Gemini API Key.
  - Keys are never stored permanently on the server (session/memory only).
- **modern UI/UX**:
  - Dark mode by default.
  - Interactive Force-Directed Graphs for system visualization.
  - Real-time streaming responses.
- **Production Ready**:
  - **Database**: Neon (Serverless Postgres).
  - **Auth**: JWT Authentication with secure session management.
  - **Deploy**: Optimized for Netlify (Frontend + Backend).

## 🛠 Tech Stack

- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, Framer Motion, React Force Graph.
- **Backend**: Python 3.9+, FastAPI, SQLAlchemy, Pydantic, NetworkX (Graph Analysis).
- **Database**: PostgreSQL (via Neon).
- **Infrastructure**: Netlify (Next.js Runtime + Python Serverless Functions).

## 📸 Screenshots

### Login & Authentication
![Login](docs/assets/login.png)

### System Visualization
![Graph](docs/assets/graph.png)

### Settings & BYOK
![Settings](docs/assets/settings.png)

### Deployment Success
![Deployment](docs/assets/deploy.png)

---

## 🏁 Getting Started (Local Development)

### Prerequisites
- Node.js 18+
- Python 3.9+
- PostgreSQL (or use SQLite locally)

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/governance-engine.git
cd governance-engine
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations (auto-creates SQLite db if no strict URL)
# or just run the app, it invokes create_all()
python -m app.main
```
Backend runs at `http://localhost:8000`.

### 3. Frontend Setup
```bash
cd frontend
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

npm run dev
```
Frontend runs at `http://localhost:3000`.

---

## ☁️ Deployment (Netlify)

This project is configured for **Zero Config Deployment** on Netlify.

### 1. Connect to Git
- Push this repo to GitHub.
- Log in to Netlify -> "Import from Git".

### 2. Configure Environment Variables
In Netlify Site Settings -> Environment Variables:
- `PYTHON_VERSION`: `3.9`
- `DATABASE_URL`: Your Neon/Postgres connection string (e.g., `postgres://user:pass@host/db`).
  - *Note: The app automatically patches `postgres://` to `postgresql://` for compatibility.*
- `NEXT_PUBLIC_API_URL`: Your Netlify URL (e.g., `https://your-site.netlify.app`).

### 3. Deploy
- Click **Deploy Site**.
- Netlify will detect `netlify.toml` and build both the Next.js frontend and the Python backend functions.

### Troubleshooting Deployment
- **404 on API**: Ensure `netlify.toml` has the correct redirect:
  ```toml
  [[redirects]]
    from = "/api/*"
    to = "/.netlify/functions/api/:splat"
    status = 200
  ```
- **Database Error**: Check function logs. Ensure `psycopg2-binary` is in `requirements.txt`.

---

## 🧠 AI Architecture

```mermaid
graph TD
    User[User Request] --> API[FastAPI Gateway]
    API --> RateLimiter{Rate Limit Check}
    RateLimiter -- OK --> Primary[Gemini 1.5 Flash]
    RateLimiter -- Exceeded --> Fallback[Gemini 1.0 Pro]
    Primary -- Success --> Response
    Primary -- 429/500 --> Fallback
    Fallback --> Response
```

The system uses a smart fallback mechanism. If the Primary model is rate-limited or fails, it seamlessly switches to the Fallback model without user intervention, adding response headers (`X-AI-Fallabck: true`) to inform the client.

## 📄 License
MIT

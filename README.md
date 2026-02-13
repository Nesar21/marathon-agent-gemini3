# Governance Engine (MVP)

> **Visualize. Validate. Improve.**
> A powerful governance tool powered by Dual Model AI (Gemini 3 Flash + 2.5 Flash).

![Dashboard](docs/assets/dashboard.png)

---

## 🌟 Visual Showcase

### 1. Interactive System Graph
See your entire architecture at a glance. Identify dependencies, circular references, and missing components instantly.
*(Visual feedback: Red nodes = Errors, Orange nodes = Warnings)*

### 2. Strict Safety Checks (DFR Engine)
Before AI even sees your plan, our **Deterministic Failure Report (DFR)** Engine runs strict logic rules. It catches:
- ❌ Circular Dependencies
- ❌ Type Mismatches
- ❌ Missing References

### 3. AI Powered Suggestions
Once safety checks pass, our **Dual AI System** analyzes your design for improvements.
It acts as a senior architect review partner.

![AI Suggestions](docs/assets/ai_suggestions.png)

### 4. Secure & Private (BYOK)
Bring Your Own Key. Your API keys are stored in memory only and never saved to our database.
![Settings](docs/assets/settings.png)

---

## 🚀 Features at a Glance

| Feature | Description |
| :--- | :--- |
| **Dual Model AI** | Primary (Gemini 3 Flash) for speed. Fallback (Gemini 2.5 Flash) for reliability. |
| **Real-Time Analysis** | Instant feedback as you validate plans. |
| **Dark Mode UI** | Modern, responsive interface built with Tailwind CSS. |
| **Production Ready** | Built on FastAPI and Next.js 14. |

---

## 🛠 Usage Guide

### Running Locally

1. **Backend Setup**:
   ```bash
   cd backend
   pip install -r requirements.txt
   python -m app.main
   ```

2. **Frontend Setup**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Access**:
   Open `http://localhost:3000`.
   Sign up with any email/password (local database).

### Usage Flow

1. **Dashboard**: Paste your JSON system plan.
2. **Validate**: Click "Validate Plan" to run DFR checks.
3. **AI Suggestions**: If critical checks pass, click "Get AI Suggestions" for architectural advice.
4. **Settings**: Enter your Gemini API Key if prompted.

---

*Governance Engine v1.0 - Built for Stability and Intelligence.*

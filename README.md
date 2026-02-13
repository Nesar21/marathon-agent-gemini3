# Governance Engine (MVP)

A simple, powerful tool to check, visualize, and improve your system plans using Dual Model AI.

---

## 📊 Dashboard & Visualization

![Dashboard](docs/assets/dashboard.png)

Understand your system instantly.
- **Interactive Graph**: See how every component connects.
- **Real-Time Stats**: Errors and warnings are highlighted immediately.
- **Visual Feedback**: Red nodes mean errors, orange means warnings. Click any node to drill down.

---

## 🛡️ DFR Engine (Deterministic Failure Report)

![Graph](docs/assets/graph.png)

**Safety First.** Before AI gets involved, our strict logic engine validates your plan:
1.  **Logical Consistency**: Are all dependencies valid?
2.  **Structural Integrity**: Do you have circular references?
3.  **Type Safety**: Are you using correct data types?

It's fast, 100% accurate, and runs instantly in your browser.

---

## 🧠 AI Suggestions (Dual Intelligence)

![AI Suggestions](docs/assets/ai_suggestions.png)

Once safety checks pass, our **Dual AI System** analyzes your architecture:
- **Primary Brain (Gemini 3 Flash)**: Fast, cost-effective analysis.
- **Fallback Brain (Gemini 2.5 Flash)**: Takes over automatically if the primary brain is busy or fails.

It provides actionable advice like:
> "Add a cache layer here to reduce load."
> "This database schema is missing an index."

---

## 🚀 How to Run (Simple)

### 1. Install & Run
```bash
# Backend
pip install -r backend/requirements.txt
python -m backend.app.main

# Frontend
cd frontend && npm install && npm run dev
```

### 2. Open It
Visit `http://localhost:3000`.

---

*Simple. Visual. Intelligent.*

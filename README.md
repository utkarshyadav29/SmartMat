# SmartMat 🚗🔬
### AI-Powered Automotive Material Selection Advisor

SmartMat is an intelligent automotive engineering advisor designed for the **Infosys IGNITE ENG NEXT 2026 Hack-AI-Thon** (Problem Statement PSE-04).

It combines multi-criteria mechanical and environmental scoring, a Decision Tree classifier, and a **Hybrid Credibility Agent** (Layer 1 verified OEM dataset ground-truth + Layer 2 Cirrascale Llama-3.3-70B forward-looking intelligence) to recommend the optimal engineering materials for automobile components.

---

## 🚀 Quick Start & Student Implementation Guide

For the full, beginner-friendly guide with step-by-step instructions and **when to open new terminals**, please refer to:

👉 **[IMPLEMENTATION_STEPS.md](file:///z:/SmartMat/IMPLEMENTATION_STEPS.md)** 👈

---

## ⚡ Quick Run Summary

### 1. Data Pipeline & Model Training (Run Once in Terminal 1)
```powershell
python merge_datasets.py      # Merges source CSVs into SmartMat_Master.csv
python scoring.py             # Calculates 1-10 scores -> materials_scored.csv
python model.py               # Trains Decision Tree -> model.pkl
```

### 2. Testing Agents (Terminal 1)
```powershell
python credibility_agent.py   # Layer 1: Deterministic CSV OEM lookup
python llm_enrichment.py      # Layer 2: Llama-3.3-70B strategic insights
python hybrid_agent.py        # Combined Layer 1 + Layer 2 report
```

### 3. Running Services (Requires 2 Separate Terminals!)
* **Terminal 1 (Backend API):**
  ```powershell
  python api.py
  ```
  *(Running continuously on http://127.0.0.1:5000 — Leave this terminal open!)*

* **Terminal 2 (Frontend UI - Open a New Terminal):**
  ```powershell
  streamlit run app.py
  ```
  *(Running continuously on http://localhost:8501 — Opens in your browser!)*

---

## 🛠 Project Structure

* `SmartMat_Master.csv`: Master automotive material database (1,552 records, 37 properties).
* `merge_datasets.py`: Data ingestion and deduplication pipeline.
* `scoring.py`: Multi-criteria engineering scoring engine.
* `model.py`: Decision Tree recommendation category classifier.
* `field_rules.py`: Hard minimum engineering thresholds with 20% relaxation fallback.
* `conflict.py`: Trade-off conflict detection and weight redistribution.
* `presets.py`: Engineering presets and sustainability filter definitions.
* `credibility_agent.py`: Layer 1 ground truth lookup (Zero hallucination).
* `llm_enrichment.py`: Layer 2 forward-looking LLM intelligence (Llama-3.3-70B).
* `hybrid_agent.py`: Orchestrator merging Layer 1 & Layer 2 with trust provenance.
* `explainer.py`: Llama-3.1-8B concise (<80 words) comparison generator.
* `api.py`: Flask REST API serving `/recommend` and `/compare`.
* `app.py`: Streamlit frontend user interface.
* `requirements.txt`: Python dependencies.
* `.env.example`: Template for environment variables.
* `IMPLEMENTATION_STEPS.md`: Comprehensive beginner-friendly execution guide.

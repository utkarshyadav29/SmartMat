# SmartMat — Complete Student Implementation & Run Guide 🚗🔬

Welcome to **SmartMat**! This guide is written step-by-step for students and beginners. It explains exactly what each script does, the exact order in which to run commands, and **crucially: when and why you need to open a new terminal**.

---

## 📌 Table of Contents
1. [Project Overview](#-1-project-overview)
2. [Prerequisites](#-2-prerequisites)
3. [Setup & Virtual Environment (Terminal 1)](#-3-setup--virtual-environment-terminal-1)
4. [Step-by-Step Execution Workflow](#-4-step-by-step-execution-workflow)
   - [Phase A: Data Pipeline & Model Training](#phase-a-data-pipeline--model-training-run-once-in-terminal-1)
   - [Phase B: Testing the Hybrid AI Agents](#phase-b-testing-the-hybrid-ai-agents-in-terminal-1)
   - [Phase C: Running Live Services (When to Open New Terminals!)](#phase-c-running-live-services-multi-terminal)
5. [Quick Terminal Summary Cheat Sheet](#-5-quick-terminal-summary-cheat-sheet)
6. [Troubleshooting FAQ](#-6-troubleshooting-faq)

---

## 📖 1. Project Overview

**SmartMat** is an AI-powered automotive material selection advisor. It solves the challenge of selecting the optimal engineering material for automobile components (such as a Chassis, Engine Block, or Suspension) by balancing mechanical strength, lightweighting, cost, elevated temperature resistance, and sustainability.

### The System Architecture:
1. **Data Pipeline** (`merge_datasets.py`): Combines mechanical properties, OEM industry usage records, and supply chain availability into a single master database (`SmartMat_Master.csv`).
2. **Scoring Engine** (`scoring.py`): Converts raw physical values (MPa, density, INR/kg, carbon footprint) into normalized $1 - 10$ engineering scores (`materials_scored.csv`).
3. **Decision Tree ML** (`model.py`): Classifies materials into 5 recommendation buckets (`model.pkl`).
4. **Hybrid Credibility Agent** (`hybrid_agent.py`):
   - **Layer 1** (`credibility_agent.py`): Deterministic CSV lookup from verified OEM automotive databases (**Zero hallucination / High Trust**).
   - **Layer 2** (`llm_enrichment.py`): Cirrascale `Llama-3.3-70B` model providing forward-looking automotive trends and risks (**Medium Trust**).
5. **LLM Explainer** (`explainer.py`): Cirrascale `Llama-3.1-8B` explaining why the top choice beats the runner-up in plain language (<80 words).
6. **Backend REST API** (`api.py`): Flask server exposing `/recommend` and `/compare` endpoints.
7. **Frontend Web UI** (`app.py`): Interactive Streamlit web interface with interactive sliders.

---

## 💻 2. Prerequisites

Before starting, ensure you have:
* **Python 3.10, 3.11, or 3.12** installed on your system.
  * Verify in terminal: `python --version`
* **VS Code** (or your preferred code editor).
* **Git** installed.

---

## ⚙ 3. Setup & Virtual Environment (Terminal 1)

Open VS Code and open your terminal (**Terminal > New Terminal** or press ``Ctrl + ` ``).

### Step 3.1: Navigate to the project directory
Make sure your terminal is inside the `SmartMat` directory:
```powershell
cd z:\SmartMat
```
*(Replace `z:\SmartMat` with your actual folder path if different)*

### Step 3.2: Create and activate a Virtual Environment
A virtual environment ensures project packages do not conflict with your global Python installation.

```powershell
# Create the virtual environment folder named 'venv'
python -m venv venv

# Activate on Windows PowerShell:
.\venv\Scripts\Activate.ps1

# (If on Windows Command Prompt instead):
# venv\Scripts\activate.bat

# (If on macOS/Linux instead):
# source venv/bin/activate
```
> 💡 *When activated, you will see `(venv)` at the beginning of your terminal line.*

### Step 3.3: Install required libraries
Install all project dependencies:
```powershell
pip install -r requirements.txt
```

### Step 3.4: Configure your `.env` API Key
The project uses Cirrascale AI Suite for Llama models.
Create a file named `.env` in the root folder (or copy from `.env.example`):
```powershell
cp .env.example .env
```
Open `.env` and verify your credentials:
```env
API_KEY=your_cirrascale_api_key_here
API_BASE_URL=https://aisuite.cirrascale.com/apis/v2
MODEL_NAME=Llama-3.1-8B
```

---

## 🚀 4. Step-by-Step Execution Workflow

---

### Phase A: Data Pipeline & Model Training (Run Once in Terminal 1)

These scripts run, process data, save files, and **finish automatically** (they return back to the command prompt). Run them one by one in **Terminal 1**.

#### 🔹 Script 1: Merge Source Datasets
Combines the 3 source CSVs (`Main_SmartMat.csv`, `Material_Industry_Evidence.csv`, `Material_Market_Availability.csv`) into `SmartMat_Master.csv`.
```powershell
python merge_datasets.py
```
* **What it does:** Deduplicates entries on `Material_Key`, performs left joins, and runs a zero-null check on critical engineering fields.
* **Expected Output:**
  ```text
  Merged shape: (1552, 37)
  [OK] SmartMat_Master.csv saved -> ...
  ```

#### 🔹 Script 2: Calculate Multi-Criteria Scores
Normalizes strength, density, cost, and embodied carbon into scores from $1.0$ to $10.0$.
```powershell
python scoring.py
```
* **What it does:** Generates `materials_scored.csv` and assigns initial recommendation categories.
* **Expected Output:**
  ```text
  Loaded 1552 material records.
  Saved 1552 rows to: ...\materials_scored.csv
  --- Recommendation Distribution ---
  ```

#### 🔹 Script 3: Train the Decision Tree Model
Trains the machine learning classifier on the scored data.
```powershell
python model.py
```
* **What it does:** Trains a scikit-learn Decision Tree to predict material recommendation categories from engineering properties and saves `model.pkl`.
* **Expected Output:**
  ```text
  Model Accuracy (Test Set): 1.0000 (100.00%)
  Saved trained category prediction model to: ...\model.pkl
  ```

---

### Phase B: Testing the Hybrid AI Agents (in Terminal 1)

Next, test the individual intelligence modules to verify that data lookups and LLM calls are functioning properly.

#### 🔹 Script 4: Test Layer 1 (Ground Truth CSV Lookup)
```powershell
python credibility_agent.py
```
* **What it does:** Searches `SmartMat_Master.csv` for verified OEM usage (e.g. BMW, Mahindra), common components, and supply-chain risk.
* **Expected Output:** Displays verified facts with `found: True`.

#### 🔹 Script 5: Test Layer 2 (Llama-3.3-70B Strategic Intelligence)
```powershell
python llm_enrichment.py
```
* **What it does:** Sends verified facts to Cirrascale's `Llama-3.3-70B` and asks for forward-looking automotive trends, global OEM usage outside India, and substitution risks.
* **Expected Output:** A clean JSON output containing `global_oem_usage`, `recent_trend`, `why_preferred`, `alternative_risk`, and `confidence`.

#### 🔹 Script 6: Test Hybrid Agent Orchestrator
```powershell
python hybrid_agent.py
```
* **What it does:** Combines Layer 1 and Layer 2 into a single report with strict trust labels (`verified_data` as High Trust, `ai_insights` as Medium Trust).
* **Expected Output:** Complete structured output displaying both layers.

---

### Phase C: Running Live Services (Multi-Terminal!)

> ⚠️ **CRITICAL CONCEPT FOR STUDENTS: WHY DO WE NEED NEW TERMINALS?**
>
> Scripts like `merge_datasets.py` do a job and exit. But servers like **Flask API** (`api.py`) and **Streamlit** (`app.py`) are **continuous background servers**.
>
> When you launch `python api.py`, the terminal stays "busy" listening for incoming requests on port 5000. It **never returns to the command prompt** until you stop it.
>
> Therefore, **you CANNOT type the next command in the same terminal**. You must leave Terminal 1 running and **OPEN A NEW TERMINAL** for the next service!

---

#### 🟢 Terminal 1: Start the Backend Flask API Server

In your current terminal (**Terminal 1**):
```powershell
python api.py
```
* **What it does:** Starts the REST API on port `5000`.
* **What you should see:**
  ```text
   * Serving Flask app 'api'
   * Debug mode: on
   * Running on http://127.0.0.1:5000
   (Press CTRL+C to quit)
  ```
* 🛑 **DO NOT CLOSE THIS TERMINAL! LEAVE IT RUNNING.**

---

#### 🟢 Terminal 2: Start the Frontend Streamlit Web UI (OPEN NEW TERMINAL!)

1. In VS Code, look at the terminal panel in the bottom right corner.
2. Click the **`+` (New Terminal)** icon (or press ``Ctrl + Shift + ` ``).
3. A fresh, clean terminal will open (**Terminal 2**).

In **Terminal 2**, run:
```powershell
# 1. Activate your virtual environment in this new terminal:
.\venv\Scripts\Activate.ps1

# 2. Launch the Streamlit application:
streamlit run app.py
```

* **What it does:** Starts the web frontend on port `8501` and connects to the models and scored datasets.
* **What you should see:**
  ```text
  You can now view your Streamlit app in your browser.

    Local URL: http://localhost:8501
    Network URL: http://...
  ```
* Your web browser will automatically open with the **SmartMat** dashboard!
* 🛑 **LEAVE TERMINAL 2 RUNNING!**

---

#### 🟢 Terminal 3 (Optional): Testing API Endpoints Directly

If you want to test the Flask API endpoints or run queries while both servers are active, open a third terminal (**Terminal 3**):

1. Click **`+` (New Terminal)** in VS Code.
2. Run test queries using PowerShell or Python:

```powershell
# Test Recommendation endpoint for Chassis:
python -c "import requests; r = requests.get('http://127.0.0.1:5000/recommend?component=Chassis&strength=9&weight=7'); print(r.json())"

# Test Head-to-Head Comparison endpoint:
python -c "import requests; r = requests.get('http://127.0.0.1:5000/compare?mat1=ANSI Steel SAE 5160&mat2=ANSI Steel SAE 1015 as-rolled'); print(r.json())"
```

---

## 📋 5. Quick Terminal Summary Cheat Sheet

| Terminal | Purpose | Command to Run | Does it stay open? |
| :--- | :--- | :--- | :--- |
| **Terminal 1** | Run data pipeline & start Backend API | 1. `python merge_datasets.py`<br>2. `python scoring.py`<br>3. `python model.py`<br>4. `python api.py` | **YES** (Keeps API running on port 5000) |
| **Terminal 2** *(New)* | Run Frontend Web Application | `streamlit run app.py` | **YES** (Keeps Web UI running on port 8501) |
| **Terminal 3** *(New, Optional)* | Ad-hoc testing, Git commands, curl | `git status`, test scripts, curl queries | No (Runs commands and returns to prompt) |

---

## ❓ 6. Troubleshooting FAQ

### Q1: PowerShell says `running scripts is disabled on this system` when activating `venv`?
**Solution:** Run this one-time command in PowerShell as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then retry `.\venv\Scripts\Activate.ps1`.

### Q2: `ModuleNotFoundError: No module named 'flask'` (or another library)?
**Solution:** Ensure your virtual environment is active (look for `(venv)` on the prompt), then reinstall dependencies:
```powershell
pip install -r requirements.txt
```

### Q3: `Port 5000 is already in use` or `Port 8501 is already in use`?
**Solution:** Another instance of `api.py` or `streamlit` is already running in the background.
* On Windows, to find and close a stuck process:
  ```powershell
  # Find process using port 5000:
  netstat -ano | findstr :5000
  # Stop the process by PID (replace <PID>):
  taskkill /PID <PID> /F
  ```
* Or in the terminal where it is running, click the terminal window and press **`Ctrl + C`**.

### Q4: How do I stop the servers when I am done?
1. Go to **Terminal 1** and press **`Ctrl + C`** on your keyboard.
2. Go to **Terminal 2** and press **`Ctrl + C`** on your keyboard.
3. Both servers will shut down gracefully.

---

🎉 **Congratulations!** You now have a complete understanding of how SmartMat works and how to run all its components.

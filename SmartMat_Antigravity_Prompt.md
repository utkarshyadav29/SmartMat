# SmartMat — Antigravity IDE Prompt
## Complete Backend + Agent Implementation

---

## CONTEXT

I am building SmartMat — an AI-powered automotive material
selection advisor for the Infosys IGNITE ENG NEXT 2026
Hack-AI-Thon (Problem Statement PSE-04).

The project folder Z:\SmartMat already contains:
- SmartMat_Master.csv (1552 rows, 37 columns — merged master dataset)
- materials_scored.csv (scored version with 1-10 scores)
- model.pkl (trained Decision Tree, 100% accuracy on categories)
- scoring.py (working — converts raw values to 1-10 scores)
- model.py (working — trains and saves Decision Tree)
- explainer.py (working — calls Cirrascale Llama-3.1-8B for explanation)
- api.py (working — Flask API with /recommend endpoint)
- app.py (basic Streamlit UI — needs major upgrade)
- .env (contains API_KEY, API_BASE_URL, MODEL_NAME)

## WHAT ALREADY WORKS
- Weighted scoring engine
- Decision Tree model (100% category accuracy)
- Llama-3.1-8B explanation via Cirrascale API
- Flask API with CORS returning top 3 + explanation
- Basic Streamlit UI with 2 sliders

## YOUR TASK

Create the following NEW files and update existing ones.
Do NOT touch scoring.py or model.py — they are working.
Do NOT retrain the model.

---

## TASK 1 — CREATE merge_datasets.py

File purpose: One-time script to merge 3 source CSVs into
SmartMat_Master.csv

Logic:
- Load Main_SmartMat.csv (22 cols, 1552 rows)
- Load Material_Industry_Evidence.csv (9 cols, 1552 rows)
- Load Material_Market_Availability.csv (9 cols, 1552 rows)
- Deduplicate Evidence and Market on Material_Key (92 duplicates exist)
- Left join all 3 on Material_Key
- Drop duplicate Material_Family_mkt column
- Save as SmartMat_Master.csv
- Expected result: 1552 rows, 37 columns, zero nulls

Column names in final master (37 total):
Material_ID, Material_Key, Standard,
Yield_Strength_MPa, Ultimate_Strength_MPa, Elongation_percent,
Brinell_Hardness_HB, Youngs_Modulus_MPa, Shear_Modulus_MPa,
Poissons_Ratio, Density_kg_m3, Reference_Temperature_C,
Yield_Strength_at_T_MPa, UTS_at_T_MPa, Thermal_Conductivity_W_mK,
CTE_1_per_K, Material_Cost_INR_per_kg, Embodied_Carbon_kgCO2e_per_kg,
Specific_Strength_MPa_m3_per_kg, Specific_Stiffness_MPa_m3_per_kg,
Strength_to_Cost_MPa_per_INRkg, Strength_to_Weight_Index,
Material_Family, Industry_Evidence_Level, OEM_Tier1_Evidence,
Industry_Examples, Common_Components, Common_Automotive_Applications,
Evidence_Status, Evidence_Source,
India_Availability, Global_Availability, Supplier_Information,
Procurement_Risk, Market_Availability_Basis,
Market_Evidence_Level, Market_Source

---

## TASK 2 — CREATE presets.py

File purpose: Default slider values for each automobile component.
Used by app.py to auto-fill sliders when user picks component type.

Create a Python dictionary called COMPONENT_PRESETS with these keys:
- Chassis / Frame
- Body Panel / Skin
- Engine Block
- Suspension Component
- Brake System
- Wheel / Rim
- Interior Structure
- Exhaust System

Each key maps to a dict with these fields:
strength, weight, cost, temp, sustainability
All values between 1 and 10.

Engineering logic for values:
Chassis: strength=9, weight=7, cost=7, temp=7, sustainability=5
Body Panel: strength=7, weight=9, cost=8, temp=5, sustainability=6
Engine Block: strength=8, weight=5, cost=6, temp=9, sustainability=4
Suspension: strength=9, weight=7, cost=7, temp=7, sustainability=5
Brake System: strength=8, weight=6, cost=7, temp=9, sustainability=5
Wheel/Rim: strength=7, weight=8, cost=7, temp=6, sustainability=6
Interior Structure: strength=5, weight=8, cost=9, temp=4, sustainability=7
Exhaust System: strength=7, weight=6, cost=6, temp=9, sustainability=4

Also create SUSTAINABILITY_FILTERS dict:
Keys: must_recycle, low_carbon, eco_label, bio_based
Each maps to a description string and a filter function description.

---

## TASK 3 — CREATE field_rules.py

File purpose: Hard minimum requirements that filter out
materials before scoring. Used to prevent wrong materials
from appearing in results regardless of scores.

Create FIELD_RULES dict with component type as key.
Each value is a dict of column name to minimum value.

Rules:
Engine Block:    UTS_at_T_MPa >= 200, Thermal_Conductivity_W_mK >= 30
Brake System:    UTS_at_T_MPa >= 200, Thermal_Conductivity_W_mK >= 20
Exhaust System:  UTS_at_T_MPa >= 150, Thermal_Conductivity_W_mK >= 15
Chassis:         Ultimate_Strength_MPa >= 400
Suspension:      Ultimate_Strength_MPa >= 500, Elongation_percent >= 10
Body Panel:      no hard minimums
Wheel/Rim:       Ultimate_Strength_MPa >= 300
Interior:        no hard minimums

Also create apply_field_rules(df, component) function that:
- Takes materials DataFrame and component name
- Applies minimum thresholds from FIELD_RULES
- Returns filtered DataFrame
- If result is empty, relaxes rules by 20% and retries once
- Returns result with note if rules were relaxed

---

## TASK 4 — CREATE conflict.py

File purpose: Detect when user requirements are impossible
to satisfy simultaneously. Alert user and suggest fix.

Create detect_conflict(ranked_df, threshold=55) function:
- Checks if top ranked material scores below threshold
- If yes: finds which property has lowest average
  across top 5 materials
- Returns tuple: (conflict_detected: bool, message: str)
- Message should say which property to relax and by how much

Create resolve_conflict(user_weights) function:
- Takes user weight dict
- Finds the highest weight property
- Suggests reducing it by 20% and redistributing
- Returns suggested new weights dict

---

## TASK 5 — CREATE credibility_agent.py

File purpose: Layer 1 of hybrid agent.
Pure CSV lookup. Zero LLM. Zero hallucination risk.
Reads SmartMat_Master.csv for verified data.

Create fetch_verified_credibility(material_key: str) function:
- Loads SmartMat_Master.csv (cache it — do not reload every call)
- Finds row matching Material_Key
- Returns dict with these fields:
  companies (from Industry_Examples)
  components (from Common_Components)
  application (from Common_Automotive_Applications)
  evidence_level (from Industry_Evidence_Level)
  evidence_status (from Evidence_Status)
  source (from Evidence_Source)
  india_availability (from India_Availability)
  global_availability (from Global_Availability)
  procurement_risk (from Procurement_Risk)
  supplier_info (from Supplier_Information)
  market_source (from Market_Source)
  found (True/False — if material not in DB)

Handle case where material_key has slight name differences
by doing case-insensitive contains match as fallback.

---

## TASK 6 — CREATE llm_enrichment.py

File purpose: Layer 2 of hybrid agent.
Calls Llama-3.3-70B on Cirrascale for AI insights.
Enriches beyond what CSV has.

API credentials come from .env file:
API_KEY, API_BASE_URL (use same as explainer.py)
MODEL_NAME for this file specifically: Llama-3.3-70B

Create fetch_llm_insights(material_key, component,
                          verified_data) function:
- Builds prompt that includes what we already know
  from verified_data so LLM adds NEW info only
- Calls Cirrascale API with Llama-3.3-70B
- temperature=0.1 (factual, not creative)
- max_tokens=300
- timeout=15 seconds

Prompt must ask LLM to return ONLY JSON with these fields:
  global_oem_usage: str
  recent_trend: str
  why_preferred: str
  alternative_risk: str
  confidence: "high" / "medium" / "low"

Parse JSON response safely.
If JSON parse fails: return fallback dict with
confidence=low and note that LLM response was unparseable.
Strip markdown code fences before parsing.

---

## TASK 7 — CREATE hybrid_agent.py

File purpose: Orchestrator that calls both layers
and returns merged result with trust labels.

Create get_hybrid_credibility(material_key, component) function:
- Step 1: Call fetch_verified_credibility from credibility_agent
- Step 2: Call fetch_llm_insights from llm_enrichment
- Step 3: Return merged dict with two top-level keys:
  verified_data (high trust — from CSV)
  ai_insights (medium trust — from LLM 70B)
  material (material_key)
  component (component)

Never mix the two data sources.
Always return them as separate labelled sections.

---

## TASK 8 — UPDATE explainer.py

Current explainer.py uses Llama-3.1-8B for plain language explanation.
Update it to accept top3 list, component name, and user requirements dict.

Update get_explanation(top3, component, user_requirements) to:
- Include component in the prompt context
- Include all 5 user requirement scores in prompt
- Ask for comparison conclusion between #1 and #2
- Keep output under 80 words
- Model stays Llama-3.1-8B (do not change to 70B)

---

## TASK 9 — UPDATE api.py

Current api.py has basic /recommend endpoint.
Add these changes:

1. Add component parameter to /recommend endpoint
   (default: "Chassis" if not provided)

2. Apply field_rules filtering before scoring
   Import apply_field_rules from field_rules.py
   Filter df before calculating scores

3. Apply conflict detection
   Import detect_conflict from conflict.py
   Run after scoring, include result in response

4. Add sustainability filters as query params:
   must_recycle=true/false
   low_carbon=true/false
   eco_label=true/false
   Apply as pre-filters on df before scoring

5. Add /compare endpoint:
   Accepts mat1 and mat2 as query params
   Returns full property rows for both materials
   Plus LLM comparison conclusion from explainer

6. Keep /recommend returning top 5 not just top 3
   Add rank field (1-5) to each result

Response structure for /recommend:
{
  "component": "Chassis",
  "conflict": false,
  "conflict_message": null,
  "results": [
    {
      "rank": 1,
      "material": "ANSI Steel SAE 5160",
      "family": "Steel",
      "scores": {
        "strength": 8.7,
        "weight": 3.2,
        "cost": 7.5,
        "temp": 8.1,
        "sustainability": 5.0,
        "total": 76.4
      },
      "explanation": "LLM explanation text here"
    }
  ]
}

---

## EXISTING FILES — DO NOT TOUCH

scoring.py — working perfectly, do not modify
model.py   — working perfectly, do not modify
model.pkl  — trained model, do not retrain
.env       — credentials, do not modify

---

## RUN ORDER AFTER ALL FILES CREATED

1. python merge_datasets.py      (creates SmartMat_Master.csv)
2. python scoring.py             (creates materials_scored.csv)
3. python model.py               (confirms model.pkl still valid)
4. python credibility_agent.py   (test CSV lookup)
5. python llm_enrichment.py      (test Llama 70B call)
6. python hybrid_agent.py        (test merged output)
7. python api.py                 (start Flask on 5000)
8. streamlit run app.py          (start UI on 8501)


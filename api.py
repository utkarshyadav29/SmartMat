"""
SmartMat REST API server.

LIVE ARCHITECTURE
-----------------
SmartMat_Master.csv
        |
        v
field_rules.py
(component-specific hard screening)
        |
        v
model.py
(requirement-aware ranking)
        |
        v
scoring.py
(five criterion scores + weighted total)
        |
        v
credibility_agent.py
(verified CSV evidence only)
        |
        v
API / Streamlit

Important:
- SmartMat_Master.csv is the ONLY live recommendation data source.
- materials_scored.csv is NOT used for live recommendations.
- User sliders dynamically change ranking weights.
- Sustainability filters are hard filters.
- Component-specific engineering rules are applied before ranking.
- Missing credibility evidence is never converted into fake OEM evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

from conflict import detect_conflict
from credibility_agent import fetch_verified_credibility
from explainer import get_explanation
from field_rules import apply_field_rules
from llm_enrichment import fetch_llm_insights
from model import rank_materials
from presets import COMPONENT_PRESETS
from scoring import add_criterion_scores, add_weighted_total


# =====================================================================
# APP
# =====================================================================

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent

MASTER_PATH = BASE_DIR / "SmartMat_Master.csv"

# Cache only AI research insights.
# Material engineering data is reloaded from the master CSV when the
# server starts. Restart Flask after changing the CSV.
_INSIGHTS_CACHE: Dict[str, Dict[str, Any]] = {}


# =====================================================================
# DATASET
# =====================================================================

def load_master_dataset() -> pd.DataFrame:
    """
    Load SmartMat_Master.csv.

    This is the single source of truth for the live API.
    """

    if not MASTER_PATH.exists():
        raise FileNotFoundError(
            f"SmartMat_Master.csv not found at: {MASTER_PATH}"
        )

    df = pd.read_csv(MASTER_PATH)

    if "Material_Key" not in df.columns:
        raise KeyError(
            "SmartMat_Master.csv must contain 'Material_Key'."
        )

    return df


# Loaded once when Flask starts.
DF_MASTER = load_master_dataset()


# =====================================================================
# HELPERS
# =====================================================================

def _to_bool(value: Any) -> bool:
    """
    Convert common query-string representations into boolean.
    """

    return str(value).strip().lower() in {
        "true",
        "1",
        "yes",
        "on",
        "checked",
    }


def _safe_float(
    value: Any,
    default: float,
) -> float:
    """
    Convert a value safely to float.
    """

    try:
        result = float(value)

        if pd.isna(result):
            return float(default)

        return result

    except (TypeError, ValueError):
        return float(default)


def _clamp_priority(value: float) -> float:
    """
    Keep UI priorities inside the intended 1..10 range.
    """

    return max(
        1.0,
        min(10.0, float(value)),
    )


def _get_priorities(
    component: str,
) -> Dict[str, float]:
    """
    Get component defaults and override them with live slider values.

    Frontend query parameters:
        strength
        weight
        cost
        temp
        sustainability
    """

    default_preset = {
        "strength": 7,
        "weight": 7,
        "cost": 7,
        "temp": 7,
        "sustainability": 5,
    }

    preset = COMPONENT_PRESETS.get(
        component,
        COMPONENT_PRESETS.get(
            "Chassis / Frame",
            default_preset,
        ),
    )

    return {
        "strength": _clamp_priority(
            _safe_float(
                request.args.get(
                    "strength",
                    preset.get("strength", 7),
                ),
                preset.get("strength", 7),
            )
        ),

        "weight": _clamp_priority(
            _safe_float(
                request.args.get(
                    "weight",
                    preset.get("weight", 7),
                ),
                preset.get("weight", 7),
            )
        ),

        "cost": _clamp_priority(
            _safe_float(
                request.args.get(
                    "cost",
                    preset.get("cost", 7),
                ),
                preset.get("cost", 7),
            )
        ),

        "temperature": _clamp_priority(
            _safe_float(
                request.args.get(
                    "temp",
                    preset.get("temp", 7),
                ),
                preset.get("temp", 7),
            )
        ),

        "sustainability": _clamp_priority(
            _safe_float(
                request.args.get(
                    "sustainability",
                    preset.get("sustainability", 5),
                ),
                preset.get("sustainability", 5),
            )
        ),
    }


def _get_constraints() -> Dict[str, bool]:
    """
    Read sustainability checkbox states.

    These are HARD filters, not ranking weights.
    """

    return {
        "must_be_recyclable": _to_bool(
            request.args.get(
                "must_recycle",
                "false",
            )
        ),

        "low_carbon_required": _to_bool(
            request.args.get(
                "low_carbon",
                "false",
            )
        ),

        "eco_label_required": _to_bool(
            request.args.get(
                "eco_label",
                "false",
            )
        ),

        "bio_based_required": _to_bool(
            request.args.get(
                "bio_based",
                "false",
            )
        ),
    }


def _get_optional_numeric(
    name: str,
) -> Optional[float]:
    """
    Read optional numeric engineering requirements.
    """

    value = request.args.get(name)

    if value is None:
        return None

    if str(value).strip() == "":
        return None

    try:
        return float(value)

    except ValueError as exc:
        raise ValueError(
            f"Invalid numeric value for '{name}': {value}"
        ) from exc


def _apply_sustainability_filters(
    df: pd.DataFrame,
    constraints: Dict[str, bool],
) -> pd.DataFrame:
    """
    Apply sustainability checkboxes as hard filters.

    Important:
    Accepts boolean True, float 1.0, int 1, and 'true'/'yes' representations.
    """

    out = df.copy()

    def _is_truthy(series: pd.Series) -> pd.Series:
        as_num = pd.to_numeric(series, errors="coerce")
        num_match = as_num.fillna(0) > 0
        str_match = series.astype(str).str.strip().str.lower().isin(["true", "1", "1.0", "yes", "y"])
        return num_match | str_match

    if constraints.get("must_be_recyclable", False):
        if "Recyclable" not in out.columns:
            return out.iloc[0:0].copy()
        out = out[_is_truthy(out["Recyclable"])]

    if constraints.get("low_carbon_required", False):
        if "Low_Carbon" not in out.columns:
            return out.iloc[0:0].copy()
        out = out[_is_truthy(out["Low_Carbon"])]

    if constraints.get("eco_label_required", False):
        if "Eco_Label" not in out.columns:
            return out.iloc[0:0].copy()
        out = out[_is_truthy(out["Eco_Label"])]

    if constraints.get("bio_based_required", False):
        if "Bio_Based" not in out.columns:
            return out.iloc[0:0].copy()
        out = out[_is_truthy(out["Bio_Based"])]

    return out

    return out


# =====================================================================
# AI INSIGHTS
# =====================================================================

def _get_material_ai_insights(
    material_key: str,
    component: str,
    verified_data: Optional[Dict[str, Any]] = None,
    call_live_llm: bool = True,
) -> Dict[str, Any]:
    """
    Get AI research insights.

    IMPORTANT:
    The fallback never invents OEMs, Tier-1 suppliers or verified usage.

    Verified evidence comes from credibility_agent.py.
    AI research is clearly separated from verified evidence.
    """

    cache_key = (
        f"{material_key}|{component}"
    ).lower()

    if cache_key in _INSIGHTS_CACHE:
        return _INSIGHTS_CACHE[cache_key]

    verified_data = verified_data or {}

    raw = None

    # -------------------------------------------------------------
    # Try LLM enrichment
    # -------------------------------------------------------------

    if call_live_llm:

        try:

            raw = fetch_llm_insights(
                material_key,
                component,
                verified_data=verified_data,
            )

        except Exception:
            raw = None

    # -------------------------------------------------------------
    # Deterministic fallback
    # -------------------------------------------------------------

    if not isinstance(raw, dict):

        companies = (
            verified_data.get("companies")
            or "No verified OEM usage found in the dataset."
        )

        components = (
            verified_data.get("components")
            or "No verified component evidence found."
        )

        raw = {
            "global_oem_usage": (
                f"Dataset evidence: {companies}"
            ),

            "recent_trend": (
                f"General engineering trend for "
                f"{component}: balancing performance, "
                "weight, cost and sustainability."
            ),

            "why_preferred": (
                f"Candidate evaluated against the "
                f"current {component} requirements."
            ),

            "alternative_risk": (
                f"Material selection outside the required "
                f"{component} engineering envelope may "
                "reduce performance margin."
            ),

            "confidence": "LOW",
        }

    # -------------------------------------------------------------
    # Never allow fake fallback OEM claims
    # -------------------------------------------------------------

    global_usage = raw.get(
        "global_oem_usage"
    )

    if not global_usage:

        global_usage = (
            "No verified global OEM usage established."
        )

    trend = (
        raw.get("recent_trend")
        or raw.get("industry_trend")
        or (
            "No specific industry trend evidence "
            "available."
        )
    )

    why_preferred = (
        raw.get("why_preferred")
        or (
            f"Evaluated against {component} "
            "requirements."
        )
    )

    risk = (
        raw.get("alternative_risk")
        or raw.get("risk_if_wrong_material")
        or (
            "Engineering margin may be affected "
            "if unsuitable material is selected."
        )
    )

    confidence = str(
        raw.get(
            "confidence",
            "LOW",
        )
    ).upper()

    if confidence not in {
        "HIGH",
        "MEDIUM",
        "LOW",
    }:
        confidence = "LOW"

    normalized = {

        "Global_OEM_Usage": global_usage,

        "global_oem_usage": global_usage,

        "Industry_Trend": trend,

        "industry_trend": trend,

        "Why_Preferred": why_preferred,

        "why_preferred": why_preferred,

        "Risk_if_Wrong_Material": risk,

        "risk_if_wrong_material": risk,

        "Confidence": confidence,

        "confidence": confidence,
    }

    _INSIGHTS_CACHE[cache_key] = normalized

    return normalized


# =====================================================================
# MATERIAL RESPONSE BUILDER
# =====================================================================

def _build_material_dict(
    row: pd.Series,
    rank_idx: int,
    component: str,
    explanation_text: str = "",
    call_live_llm: bool = False,
) -> Dict[str, Any]:
    """
    Convert ranked material row into the frontend JSON structure.
    """

    mat_key = str(
        row["Material_Key"]
    )

    family = str(
        row.get(
            "Material_Family",
            "Alloy / Metal",
        )
    )

    # -------------------------------------------------------------
    # Scores
    # -------------------------------------------------------------

    strength_score = round(
        float(
            row.get(
                "strength_score",
                0.0,
            )
        ),
        1,
    )

    weight_score = round(
        float(
            row.get(
                "weight_score",
                0.0,
            )
        ),
        1,
    )

    cost_score = round(
        float(
            row.get(
                "cost_score",
                0.0,
            )
        ),
        1,
    )

    temp_score = round(
        float(
            row.get(
                "temperature_score",
                0.0,
            )
        ),
        1,
    )

    sustainability_score = round(
        float(
            row.get(
                "sustainability_score",
                0.0,
            )
        ),
        1,
    )

    final_score = round(
        float(
            row.get(
                "final_score",
                0.0,
            )
        ),
        2,
    )

    # UI uses 0-100.
    total_score = round(
        float(
            row.get(
                "total_score",
                final_score * 10.0,
            )
        ),
        1,
    )

    # -------------------------------------------------------------
    # Verified credibility
    # -------------------------------------------------------------

    cred = fetch_verified_credibility(
        mat_key,
        requested_component=component,
    )

    india_avail = cred.get(
        "india_availability",
        "Unknown",
    )

    if india_avail in {
        None,
        "",
        "Unknown",
    }:
        india_avail = str(
            row.get(
                "India_Availability",
                "Unknown",
            )
        )

    global_avail = cred.get(
        "global_availability",
        "Unknown",
    )

    if global_avail in {
        None,
        "",
        "Unknown",
    }:
        global_avail = str(
            row.get(
                "Global_Availability",
                "Unknown",
            )
        )

    procurement_risk = cred.get(
        "procurement_risk",
        "Unknown",
    )

    if procurement_risk in {
        None,
        "",
        "Unknown",
    }:
        procurement_risk = str(
            row.get(
                "Procurement_Risk",
                "Unknown",
            )
        )

    industry_examples = cred.get(
        "companies",
        "No verified industry examples found",
    )

    common_components = cred.get(
        "components",
        "Unknown",
    )

    evidence_status = cred.get(
        "evidence_status",
        "Unverified",
    )

    evidence_source = cred.get(
        "source",
        "Unknown",
    )

    credibility = cred.get(
        "credibility",
        "UNVERIFIED",
    )

    # -------------------------------------------------------------
    # Cost / carbon
    # -------------------------------------------------------------

    cost_value = row.get(
        "Material_Cost_INR_per_kg"
    )

    carbon_value = row.get(
        "Embodied_Carbon_kgCO2e_per_kg"
    )

    if pd.notna(cost_value):

        cost_str = (
            f"{float(cost_value):.1f}"
        )

    else:

        cost_str = "Unknown"

    if pd.notna(carbon_value):

        carbon_str = (
            f"{float(carbon_value):.2f}"
        )

    else:

        carbon_str = "Unknown"

    # -------------------------------------------------------------
    # AI insights
    # -------------------------------------------------------------

    insights = _get_material_ai_insights(
        mat_key,
        component=component,

        verified_data={
            "companies": industry_examples,
            "components": common_components,
            "procurement_risk": procurement_risk,
            "Material_Family": family,
        },

        call_live_llm=call_live_llm,
    )

    # -------------------------------------------------------------
    # Raw engineering properties
    # -------------------------------------------------------------

    def numeric_value(
        column: str,
    ) -> Optional[float]:

        value = row.get(column)

        if value is None:
            return None

        try:

            if pd.isna(value):
                return None

            return float(value)

        except (TypeError, ValueError):

            return None

    def bool_value(
        column: str,
    ) -> bool:

        value = row.get(
            column,
            False,
        )

        if pd.isna(value):
            return False

        if isinstance(value, bool):
            return value

        return str(value).strip().lower() in {
            "true",
            "1",
            "yes",
        }

    return {

        # ---------------------------------------------------------
        # Identity
        # ---------------------------------------------------------

        "rank": rank_idx,

        "material": mat_key,

        "material_name": mat_key,

        "Material_Name": mat_key,

        "Material_Key": mat_key,

        "name": mat_key,

        "family": family,

        "material_family": family,

        "Material_Family": family,

        # ---------------------------------------------------------
        # Final ranking
        # ---------------------------------------------------------

        "total_score": total_score,

        "Total_Score": total_score,

        "score": total_score,

        "final_score": final_score,

        # ---------------------------------------------------------
        # Criterion scores
        # ---------------------------------------------------------

        "strength_score": strength_score,

        "Strength_Score": strength_score,

        "weight_score": weight_score,

        "Weight_Score": weight_score,

        "cost_score": cost_score,

        "Cost_Score": cost_score,

        "temp_score": temp_score,

        "temperature_score": temp_score,

        "Temperature_Score": temp_score,

        "sustainability_score": sustainability_score,

        "Sustainability_Score": sustainability_score,

        "scores": {
            "strength": strength_score,
            "weight": weight_score,
            "cost": cost_score,
            "temp": temp_score,
            "sustainability": sustainability_score,
            "total": total_score,
        },

        # ---------------------------------------------------------
        # Explanation
        # ---------------------------------------------------------

        "explanation": explanation_text,

        # ---------------------------------------------------------
        # Credibility
        # ---------------------------------------------------------

        "Credibility": credibility,

        "credibility": credibility,

        "India_Availability": india_avail,

        "india_availability": india_avail,

        "Global_Availability": global_avail,

        "global_availability": global_avail,

        "Procurement_Risk": procurement_risk,

        "procurement_risk": procurement_risk,

        "Industry_Examples": industry_examples,

        "industry_examples": industry_examples,

        "Common_Components": common_components,

        "common_components": common_components,

        "Evidence_Status": evidence_status,

        "evidence_status": evidence_status,

        "Evidence_Source": evidence_source,

        "evidence_source": evidence_source,

        # ---------------------------------------------------------
        # Economics / sustainability
        # ---------------------------------------------------------

        "Material_Cost": cost_str,

        "material_cost": cost_str,

        "cost_inr_kg": cost_str,

        "Embodied_Carbon": carbon_str,

        "embodied_carbon": carbon_str,

        # ---------------------------------------------------------
        # Engineering properties
        # ---------------------------------------------------------

        "Yield_Strength_MPa": numeric_value(
            "Yield_Strength_MPa"
        ),

        "yield_strength_mpa": numeric_value(
            "Yield_Strength_MPa"
        ),

        "Ultimate_Strength_MPa": numeric_value(
            "Ultimate_Strength_MPa"
        ),

        "ultimate_strength_mpa": numeric_value(
            "Ultimate_Strength_MPa"
        ),

        "Density_kg_m3": numeric_value(
            "Density_kg_m3"
        ),

        "density_kg_m3": numeric_value(
            "Density_kg_m3"
        ),

        "Max_Service_Temperature_C": numeric_value(
            "Max_Service_Temperature_C"
        ),

        "max_service_temperature_c": numeric_value(
            "Max_Service_Temperature_C"
        ),

        # ---------------------------------------------------------
        # Sustainability flags
        # ---------------------------------------------------------

        "Recyclable": bool_value(
            "Recyclable"
        ),

        "Low_Carbon": bool_value(
            "Low_Carbon"
        ),

        "Eco_Label": bool_value(
            "Eco_Label"
        ),

        "Bio_Based": bool_value(
            "Bio_Based"
        ),

        # ---------------------------------------------------------
        # AI research section
        # ---------------------------------------------------------

        **insights,
    }


# =====================================================================
# HOME
# =====================================================================

@app.route("/")
def home():

    return jsonify({

        "status": "online",

        "service": (
            "SmartMat Automotive Material "
            "Selection Advisor API"
        ),

        "version": "4.0",

        "data_source": "SmartMat_Master.csv",

        "scored_csv_is_live_source": False,

        "architecture": (
            "Master CSV -> component hard rules -> "
            "requirement-aware scoring -> weighted ranking"
        ),

        "endpoints": {

            "/recommend":
                "Dynamic Top-5 material ranking",

            "/ranges":
                "Engineering interpretation of slider priorities",

            "/compare":
                "Head-to-head comparison",
        },

        "example_recommend": (
            "/recommend?"
            "component=Chassis%20/%20Frame"
            "&strength=9"
            "&weight=7"
            "&cost=7"
            "&temp=7"
            "&sustainability=5"
        ),

        "example_compare": (
            "/compare?"
            "mat1=ANSI%20Steel%20SAE%205160"
            "&mat2=ANSI%20Steel%20SAE%201015%20as-rolled"
        ),
    })


# =====================================================================
# RECOMMEND
# =====================================================================

@app.route(
    "/recommend",
    methods=["GET"],
)
def recommend():

    try:

        # -------------------------------------------------------------
        # Component
        # -------------------------------------------------------------

        component = request.args.get(
            "component",
            "Chassis / Frame",
        ).strip()

        # -------------------------------------------------------------
        # User priorities
        # -------------------------------------------------------------

        priorities = _get_priorities(
            component
        )

        # -------------------------------------------------------------
        # Sustainability filters
        # -------------------------------------------------------------

        constraints = _get_constraints()

        # -------------------------------------------------------------
        # Optional explicit engineering requirements
        # -------------------------------------------------------------

        required_yield = _get_optional_numeric(
            "required_yield_strength_mpa"
        )

        required_uts = _get_optional_numeric(
            "required_ultimate_strength_mpa"
        )

        required_temp = _get_optional_numeric(
            "required_temperature_c"
        )

        # -------------------------------------------------------------
        # STEP 1:
        # Component-specific hard engineering rules
        # -------------------------------------------------------------

        filtered_df, rules_note = apply_field_rules(
            DF_MASTER.copy(),
            component=component,
            return_note=True,
        )

        if filtered_df.empty:

            return jsonify({

                "component": component,

                "priorities": priorities,

                "filters": constraints,

                "conflict": True,

                "conflict_message": (
                    f"No materials satisfy the hard "
                    f"engineering rules for {component}."
                ),

                "rules_note": rules_note,

                "candidate_count": 0,

                "results": [],
            })

        # -------------------------------------------------------------
        # STEP 2:
        # Sustainability hard filters
        # -------------------------------------------------------------

        filtered_df = _apply_sustainability_filters(
            filtered_df,
            constraints,
        )

        if filtered_df.empty:

            return jsonify({

                "component": component,

                "priorities": priorities,

                "filters": constraints,

                "conflict": True,

                "conflict_message": (
                    "No materials satisfy both the "
                    "component engineering rules and "
                    "the selected sustainability filters."
                ),

                "rules_note": rules_note,

                "candidate_count": 0,

                "results": [],
            })

        candidate_count = len(
            filtered_df
        )

        # -------------------------------------------------------------
        # STEP 3:
        # Requirement-aware weighted ranking
        # -------------------------------------------------------------

        ranked = rank_materials(

            filtered_df,

            priorities=priorities,

            required_yield_strength_mpa=required_yield,

            required_ultimate_strength_mpa=required_uts,

            required_temperature_c=required_temp,

            top_n=5,

            **constraints,
        )

        if ranked.empty:

            return jsonify({

                "component": component,

                "priorities": priorities,

                "filters": constraints,

                "conflict": True,

                "conflict_message": (
                    "No materials satisfied the active "
                    "engineering and sustainability constraints."
                ),

                "rules_note": rules_note,

                "candidate_count": candidate_count,

                "results": [],
            })

        # -------------------------------------------------------------
        # Conflict detection
        # -------------------------------------------------------------

        conflict_detected, conflict_msg = (
            detect_conflict(
                ranked,
                threshold=55.0,
            )
        )

        # -------------------------------------------------------------
        # Explanation
        # -------------------------------------------------------------

        top_names = (
            ranked[
                "Material_Key"
            ]
            .head(3)
            .tolist()
        )

        try:

            explanation_text = get_explanation(

                top_names,

                component=component,

                user_requirements={

                    "strength":
                        priorities["strength"],

                    "weight":
                        priorities["weight"],

                    "cost":
                        priorities["cost"],

                    "temp":
                        priorities["temperature"],

                    "sustainability":
                        priorities["sustainability"],
                },
            )

        except Exception:

            explanation_text = (
                "Ranking generated from the current "
                "engineering criteria, component rules "
                "and user priorities."
            )

        # -------------------------------------------------------------
        # Build results
        # -------------------------------------------------------------

        results = [

            _build_material_dict(

                row=row,

                rank_idx=int(
                    row["rank"]
                ),

                component=component,

                explanation_text=explanation_text,

                call_live_llm=False,
            )

            for _, row in ranked.iterrows()
        ]

        return jsonify({

            "component": component,

            "priorities": priorities,

            "filters": constraints,

            "candidate_count": candidate_count,

            "rules_note": rules_note,

            "conflict": bool(
                conflict_detected
            ),

            "conflict_message": conflict_msg,

            "results": results,
        })

    except (
        KeyError,
        ValueError,
        TypeError,
    ) as exc:

        return jsonify({
            "error": str(exc)
        }), 400

    except Exception as exc:

        app.logger.exception(
            "Recommendation failed"
        )

        return jsonify({
            "error": str(exc)
        }), 500


# =====================================================================
# RANGES
# =====================================================================

@app.route(
    "/ranges",
    methods=["GET"],
)
def ranges():
    """
    Return dataset-driven engineering ranges for the sliders.

    These are screening/favored bands.

    They are NOT certified material allowables.
    """

    try:

        component = request.args.get(
            "component",
            "Chassis / Frame",
        ).strip()

        priorities = _get_priorities(
            component
        )

        constraints = _get_constraints()

        # -------------------------------------------------------------
        # Component rules
        # -------------------------------------------------------------

        filtered = apply_field_rules(
            DF_MASTER.copy(),
            component=component,
        )

        # -------------------------------------------------------------
        # Sustainability filters
        # -------------------------------------------------------------

        filtered = _apply_sustainability_filters(
            filtered,
            constraints,
        )

        if filtered.empty:

            return jsonify({

                "component": component,

                "candidate_count": 0,

                "priorities": priorities,

                "ranges": {},

                "note": (
                    "No materials remain after the "
                    "active component and sustainability filters."
                ),
            })

        # -------------------------------------------------------------
        # Engineering favored range
        # -------------------------------------------------------------

        def favored_band(
            column: str,
            priority: float,
            higher_is_better: bool,
        ):

            if column not in filtered.columns:
                return None

            series = pd.to_numeric(
                filtered[column],
                errors="coerce",
            ).dropna()

            if series.empty:
                return None

            p = max(
                1,
                min(
                    10,
                    int(round(priority)),
                ),
            )

            # Priority 1:
            # broad lower-demand region.
            #
            # Priority 10:
            # upper-demand region.

            q_low = (
                0.10
                + (p - 1)
                * 0.40
                / 9.0
            )

            q_high = (
                0.50
                + (p - 1)
                * 0.50
                / 9.0
            )

            if not higher_is_better:

                q_low, q_high = (
                    1.0 - q_high,
                    1.0 - q_low,
                )

            return {

                "favored_low": round(
                    float(
                        series.quantile(
                            q_low
                        )
                    ),
                    2,
                ),

                "favored_high": round(
                    float(
                        series.quantile(
                            q_high
                        )
                    ),
                    2,
                ),

                "dataset_min": round(
                    float(
                        series.min()
                    ),
                    2,
                ),

                "dataset_max": round(
                    float(
                        series.max()
                    ),
                    2,
                ),
            }

        ranges_out = {

            "strength": favored_band(
                "Yield_Strength_MPa",
                priorities["strength"],
                True,
            ),

            "weight": favored_band(
                "Density_kg_m3",
                priorities["weight"],
                False,
            ),

            "cost": favored_band(
                "Material_Cost_INR_per_kg",
                priorities["cost"],
                False,
            ),

            "temp": favored_band(
                "Max_Service_Temperature_C",
                priorities["temperature"],
                True,
            ),

            "sustainability": favored_band(
                "Embodied_Carbon_kgCO2e_per_kg",
                priorities["sustainability"],
                False,
            ),
        }

        return jsonify({

            "component": component,

            "candidate_count": int(
                len(filtered)
            ),

            "priorities": priorities,

            "ranges": ranges_out,

            "note": (
                "Dataset-driven screening band. "
                "Verify grade-specific allowables "
                "before design release."
            ),
        })

    except Exception as exc:

        app.logger.exception(
            "Range calculation failed"
        )

        return jsonify({
            "error": str(exc)
        }), 500


# =====================================================================
# COMPARE
# =====================================================================

@app.route(
    "/compare",
    methods=["GET"],
)
def compare():

    mat1 = request.args.get(
        "mat1",
        "",
    ).strip()

    mat2 = request.args.get(
        "mat2",
        "",
    ).strip()

    component = request.args.get(
        "component",
        "Chassis / Frame",
    ).strip()

    if not mat1 or not mat2:

        return jsonify({

            "error": (
                "Both 'mat1' and 'mat2' "
                "query parameters are required."
            ),

            "example": (
                "/compare?"
                "mat1=ANSI%20Steel%20SAE%205160"
                "&mat2=ANSI%20Steel%20SAE%201015%20as-rolled"
            ),
        }), 400

    # -------------------------------------------------------------
    # Comparison priorities
    # -------------------------------------------------------------

    priorities = {

        "strength": _clamp_priority(
            _safe_float(
                request.args.get(
                    "strength",
                    7,
                ),
                7,
            )
        ),

        "weight": _clamp_priority(
            _safe_float(
                request.args.get(
                    "weight",
                    7,
                ),
                7,
            )
        ),

        "cost": _clamp_priority(
            _safe_float(
                request.args.get(
                    "cost",
                    7,
                ),
                7,
            )
        ),

        "temperature": _clamp_priority(
            _safe_float(
                request.args.get(
                    "temp",
                    7,
                ),
                7,
            )
        ),

        "sustainability": _clamp_priority(
            _safe_float(
                request.args.get(
                    "sustainability",
                    7,
                ),
                7,
            )
        ),
    }

    # -------------------------------------------------------------
    # Find materials
    # -------------------------------------------------------------

    def find_row(
        name: str,
    ) -> Optional[pd.Series]:

        exact = DF_MASTER[
            DF_MASTER["Material_Key"]
            == name
        ]

        if not exact.empty:
            return exact.iloc[0]

        lower = DF_MASTER[
            DF_MASTER["Material_Key"]
            .astype(str)
            .str.lower()
            == name.lower()
        ]

        if not lower.empty:
            return lower.iloc[0]

        partial = DF_MASTER[
            DF_MASTER["Material_Key"]
            .astype(str)
            .str.lower()
            .str.contains(
                name.lower(),
                regex=False,
                na=False,
            )
        ]

        if not partial.empty:
            return partial.iloc[0]

        return None

    row1 = find_row(mat1)
    row2 = find_row(mat2)

    if row1 is None:

        return jsonify({
            "error": (
                f"Material '{mat1}' "
                "not found in dataset."
            )
        }), 404

    if row2 is None:

        return jsonify({
            "error": (
                f"Material '{mat2}' "
                "not found in dataset."
            )
        }), 404

    # -------------------------------------------------------------
    # Comparison scoring
    #
    # SAME scoring engine as recommendation.
    # -------------------------------------------------------------

    comparison_df = pd.DataFrame(
        [row1, row2]
    ).reset_index(drop=True)

    comparison_df = add_criterion_scores(
        comparison_df
    )

    comparison_df = add_weighted_total(
        comparison_df,
        priorities,
    )

    # -------------------------------------------------------------
    # Material dictionaries
    # -------------------------------------------------------------

    dict1 = _build_material_dict(
        comparison_df.iloc[0],
        1,
        component,
        call_live_llm=True,
    )

    dict2 = _build_material_dict(
        comparison_df.iloc[1],
        2,
        component,
        call_live_llm=False,
    )

    # -------------------------------------------------------------
    # LLM comparison conclusion
    # -------------------------------------------------------------

    try:

        comparison_text = get_explanation(

            [
                dict1["material"],
                dict2["material"],
            ],

            component=component,

            user_requirements={

                "strength":
                    priorities["strength"],

                "weight":
                    priorities["weight"],

                "cost":
                    priorities["cost"],

                "temp":
                    priorities["temperature"],

                "sustainability":
                    priorities["sustainability"],
            },
        )

    except Exception:

        comparison_text = (
            "Comparison generated from the current "
            "engineering criteria and user priorities."
        )

    # -------------------------------------------------------------
    # Substitute materials
    # -------------------------------------------------------------

    substitutes = []

    try:

        pool = apply_field_rules(
            DF_MASTER.copy(),
            component=component,
        )

        pool = _apply_sustainability_filters(
            pool,
            _get_constraints(),
        )

        ranked_pool = rank_materials(
            pool,
            priorities=priorities,
            top_n=8,
        )

        for _, subrow in ranked_pool.iterrows():

            key = str(
                subrow["Material_Key"]
            )

            if key in {
                dict1["Material_Key"],
                dict2["Material_Key"],
            }:
                continue

            final_score = float(
                subrow.get(
                    "final_score",
                    0.0,
                )
            )

            substitutes.append({

                "material": key,

                "family": str(
                    subrow.get(
                        "Material_Family",
                        "Other",
                    )
                ),

                "score": round(
                    final_score * 10.0,
                    1,
                ),

                "reason": (
                    "Nearby candidate under the "
                    "same component rules and "
                    "user priorities."
                ),
            })

            if len(substitutes) == 3:
                break

    except Exception:

        substitutes = []

    return jsonify({

        "component": component,

        "priorities": priorities,

        "materials": [
            dict1,
            dict2,
        ],

        "material_1": dict1,

        "material_2": dict2,

        "conclusion": comparison_text,

        "comparison_conclusion": comparison_text,

        "substitutes": substitutes,
    })


# =====================================================================
# HEALTH / DEBUG
# =====================================================================

@app.route(
    "/health",
    methods=["GET"],
)
def health():

    return jsonify({

        "status": "healthy",

        "dataset": "SmartMat_Master.csv",

        "material_count": int(
            len(DF_MASTER)
        ),

        "components": [
            "Chassis / Frame",
            "Body Panel / Skin",
            "Engine Block",
            "Suspension Component",
            "Brake System",
            "Wheel / Rim",
            "Interior Structure",
            "Exhaust System",
        ],
    })


# =====================================================================
# MAIN
# =====================================================================

if __name__ == "__main__":

    print(
        "\n=========================================="
    )

    print(
        " SmartMat API"
    )

    print(
        "=========================================="
    )

    print(
        f"Dataset: {MASTER_PATH}"
    )

    print(
        f"Materials loaded: {len(DF_MASTER)}"
    )

    print(
        "Live source: SmartMat_Master.csv"
    )

    print(
        "Scored CSV used for live ranking: NO"
    )

    print(
        "Server: http://127.0.0.1:5000"
    )

    print(
        "==========================================\n"
    )

    app.run(
        debug=True,
        port=5000,
    )
"""
api.py
SmartMat REST API server built with Flask and CORS.
Provides intelligent automotive material recommendations, component-specific field rule filtering,
conflict detection, sustainability pre-filtering, and head-to-head comparison endpoints.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

from explainer import get_explanation
from field_rules import apply_field_rules
from conflict import detect_conflict
from presets import COMPONENT_PRESETS

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent


def _compute_temp_score(series: pd.Series) -> pd.Series:
    """Normalize UTS_at_T_MPa to 1.0 - 10.0 scale."""
    s = pd.to_numeric(series, errors="coerce")
    s_min = s.min()
    s_max = s.max()
    if s_max == s_min:
        return pd.Series(5.0, index=series.index)
    return (1.0 + 9.0 * (s - s_min) / (s_max - s_min)).round(2)


def load_dataset() -> pd.DataFrame:
    """Load scored dataset and enrich with Master metadata (e.g. Material_Family)."""
    scored_path = BASE_DIR / "materials_scored.csv"
    master_path = BASE_DIR / "SmartMat_Master.csv"

    if not scored_path.exists():
        raise FileNotFoundError(f"materials_scored.csv not found at: {scored_path}")

    df_scored = pd.read_csv(scored_path)

    # Merge Material_Family and additional columns if master file exists
    if master_path.exists():
        df_master = pd.read_csv(master_path)
        meta_cols = ["Material_Key", "Material_Family", "India_Availability", "Procurement_Risk"]
        existing_meta = [c for c in meta_cols if c in df_master.columns]
        dedup_master = df_master[existing_meta].drop_duplicates(subset="Material_Key", keep="first")
        df_merged = df_scored.merge(dedup_master, on="Material_Key", how="left")
    else:
        df_merged = df_scored.copy()
        if "Material_Family" not in df_merged.columns:
            df_merged["Material_Family"] = "Alloy / Metal"

    # Ensure temperature score is present
    if "temp_score" not in df_merged.columns:
        if "UTS_at_T_MPa" in df_merged.columns:
            df_merged["temp_score"] = _compute_temp_score(df_merged["UTS_at_T_MPa"])
        else:
            df_merged["temp_score"] = 5.0

    return df_merged


DF_MASTER = load_dataset()


def _apply_sustainability_filters(
    df_in: pd.DataFrame,
    must_recycle: bool,
    low_carbon: bool,
    eco_label: bool,
) -> pd.DataFrame:
    """Apply boolean sustainability pre-filters prior to ranking."""
    res = df_in.copy()

    if must_recycle and "Material_Family" in res.columns:
        recyclable_families = [
            "Steel",
            "Aluminum",
            "Copper alloys",
            "Cast iron",
            "Stainless steel",
            "Magnesium",
            "Tin alloys",
        ]
        filtered = res[res["Material_Family"].isin(recyclable_families)]
        if not filtered.empty:
            res = filtered

    if low_carbon and "Embodied_Carbon_kgCO2e_per_kg" in res.columns:
        carbon_num = pd.to_numeric(res["Embodied_Carbon_kgCO2e_per_kg"], errors="coerce")
        filtered = res[carbon_num <= 5.0]
        if not filtered.empty:
            res = filtered

    if eco_label and "sustainability_score" in res.columns:
        sust_num = pd.to_numeric(res["sustainability_score"], errors="coerce")
        filtered = res[(sust_num >= 6.5) | (res.get("recommendation") == "Eco-Friendly Material")]
        if not filtered.empty:
            res = filtered

    return res


@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "service": "SmartMat Automotive Material Selection Advisor API",
        "version": "2.0",
        "endpoints": {
            "/recommend": "Get top 5 ranked materials with field rules, conflict check, and AI explanation",
            "/compare": "Head-to-head property comparison and LLM conclusion between two materials (mat1, mat2)",
        },
        "example_recommend": "/recommend?component=Chassis&strength=9&weight=7&cost=7&temp=7&sustainability=5",
        "example_compare": "/compare?mat1=ANSI Steel SAE 5160&mat2=ANSI Steel SAE 1015 as-rolled",
    })


@app.route("/recommend", methods=["GET"])
def recommend():
    component = request.args.get("component", "Chassis").strip()

    # Retrieve component preset defaults
    preset = COMPONENT_PRESETS.get(component, COMPONENT_PRESETS["Chassis"])

    # Read slider weights with preset fallbacks
    strength = float(request.args.get("strength", preset["strength"]))
    weight = float(request.args.get("weight", preset["weight"]))
    cost = float(request.args.get("cost", preset["cost"]))
    temp = float(request.args.get("temp", preset["temp"]))
    sustainability = float(request.args.get("sustainability", preset["sustainability"]))

    user_requirements = {
        "strength": strength,
        "weight": weight,
        "cost": cost,
        "temp": temp,
        "sustainability": sustainability,
    }

    # Read sustainability boolean flags
    must_recycle = request.args.get("must_recycle", "false").lower() in ("true", "1", "yes")
    low_carbon = request.args.get("low_carbon", "false").lower() in ("true", "1", "yes")
    eco_label = request.args.get("eco_label", "false").lower() in ("true", "1", "yes")

    # Step 1: Apply sustainability pre-filters
    filtered_df = _apply_sustainability_filters(
        DF_MASTER,
        must_recycle=must_recycle,
        low_carbon=low_carbon,
        eco_label=eco_label,
    )

    # Step 2: Apply field rules for the specific component
    filtered_df = apply_field_rules(filtered_df, component=component)

    if filtered_df.empty:
        return jsonify({
            "component": component,
            "conflict": True,
            "conflict_message": f"No materials satisfied constraints for {component}.",
            "results": [],
        })

    # Step 3: Compute weighted total score (normalized to 0 - 100)
    w_sum = strength + weight + cost + temp + sustainability
    if w_sum <= 0:
        w_sum = 1.0

    scored_temp = filtered_df.copy()
    scored_temp["total_score"] = (
        (
            scored_temp["strength_score"] * strength
            + scored_temp["weight_score"] * weight
            + scored_temp["cost_score"] * cost
            + scored_temp["temp_score"] * temp
            + scored_temp["sustainability_score"] * sustainability
        )
        / w_sum
        * 10.0
    ).round(1)

    # Step 4: Sort descending and check for requirement trade-off conflicts
    ranked = scored_temp.sort_values("total_score", ascending=False)
    conflict_detected, conflict_msg = detect_conflict(ranked, threshold=55.0)

    # Step 5: Get top 5 results
    top5_df = ranked.head(5)
    top3_names = top5_df["Material_Key"].head(3).tolist()

    # Step 6: Generate AI explanation via Llama-3.1-8B
    explanation_text = get_explanation(top3_names, component=component, user_requirements=user_requirements)

    results = []
    for rank_idx, (_, row) in enumerate(top5_df.iterrows(), start=1):
        results.append({
            "rank": rank_idx,
            "material": str(row["Material_Key"]),
            "family": str(row.get("Material_Family", "Steel")),
            "scores": {
                "strength": round(float(row.get("strength_score", 0.0)), 1),
                "weight": round(float(row.get("weight_score", 0.0)), 1),
                "cost": round(float(row.get("cost_score", 0.0)), 1),
                "temp": round(float(row.get("temp_score", 0.0)), 1),
                "sustainability": round(float(row.get("sustainability_score", 0.0)), 1),
                "total": round(float(row.get("total_score", 0.0)), 1),
            },
            "explanation": explanation_text,
        })

    return jsonify({
        "component": component,
        "conflict": conflict_detected,
        "conflict_message": conflict_msg,
        "results": results,
    })


@app.route("/compare", methods=["GET"])
def compare():
    mat1 = request.args.get("mat1", "").strip()
    mat2 = request.args.get("mat2", "").strip()

    if not mat1 or not mat2:
        return jsonify({
            "error": "Both 'mat1' and 'mat2' query parameters are required.",
            "example": "/compare?mat1=ANSI Steel SAE 5160&mat2=ANSI Steel SAE 1015 as-rolled",
        }), 400

    def _find_row(name: str):
        match = DF_MASTER[DF_MASTER["Material_Key"] == name]
        if match.empty:
            match = DF_MASTER[DF_MASTER["Material_Key"].str.lower() == name.lower()]
        if match.empty:
            match = DF_MASTER[DF_MASTER["Material_Key"].str.lower().str.contains(name.lower(), regex=False, na=False)]
        return match.iloc[0].to_dict() if not match.empty else None

    row1 = _find_row(mat1)
    row2 = _find_row(mat2)

    if not row1:
        return jsonify({"error": f"Material '{mat1}' not found in dataset."}), 404
    if not row2:
        return jsonify({"error": f"Material '{mat2}' not found in dataset."}), 404

    # Sanitize float NaNs for valid JSON
    def _sanitize(d: dict) -> dict:
        return {k: (None if pd.isna(v) else v) for k, v in d.items()}

    clean_row1 = _sanitize(row1)
    clean_row2 = _sanitize(row2)

    # Call explainer for head-to-head comparison
    comparison_text = get_explanation(
        [clean_row1["Material_Key"], clean_row2["Material_Key"]],
        component="Vehicle Component",
        user_requirements={"strength": 7, "weight": 7, "cost": 7, "temp": 7, "sustainability": 7},
    )

    return jsonify({
        "material_1": clean_row1,
        "material_2": clean_row2,
        "comparison_conclusion": comparison_text,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
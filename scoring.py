"""
scoring.py
"""

from pathlib import Path
import pandas as pd


def compute_strength_score(su_series: pd.Series, decimals: int = 2) -> pd.Series:
    su_min = su_series.min()
    su_max = su_series.max()
    if su_max == su_min:
        return pd.Series(5.0, index=su_series.index)
    score = 1.0 + 9.0 * (su_series - su_min) / (su_max - su_min)
    return score.round(decimals)


def compute_weight_score(ro_series: pd.Series, decimals: int = 2) -> pd.Series:
    ro_min = ro_series.min()
    ro_max = ro_series.max()
    if ro_max == ro_min:
        return pd.Series(5.0, index=ro_series.index)
    score = 1.0 + 9.0 * (ro_max - ro_series) / (ro_max - ro_min)
    return score.round(decimals)


def compute_cost_score(cost_series: pd.Series,
                       decimals: int = 2) -> pd.Series:
    """
    Lower cost = higher score (inverse scaling).
    Uses real INR per kg values from dataset.
    Fills nulls with median before scaling.
    """
    filled = cost_series.fillna(cost_series.median())
    c_min  = filled.min()
    c_max  = filled.max()
    if c_max == c_min:
        return pd.Series(5.0, index=cost_series.index)
    score = 1.0 + 9.0 * (c_max - filled) / (c_max - c_min)
    return score.round(decimals)


def compute_sustainability_score(carbon_series: pd.Series,
                                  decimals: int = 2) -> pd.Series:
    """
    Lower embodied carbon = higher sustainability score.
    Fills nulls with worst case (highest carbon value).
    """
    filled = carbon_series.fillna(carbon_series.max())
    c_min  = filled.min()
    c_max  = filled.max()
    if c_max == c_min:
        return pd.Series(5.0, index=carbon_series.index)
    score = 1.0 + 9.0 * (c_max - filled) / (c_max - c_min)
    return score.round(decimals)


def estimate_material_cost_score(material_name: str, strength_score: float, weight_score: float) -> float:
    mat = str(material_name).lower()
    if "steel" in mat or "iron" in mat:
        return 7.5 if strength_score >= 6 else 7.0
    elif "aluminum" in mat or "al " in mat:
        return 8.0 if weight_score >= 7 else 6.5
    elif "magnesium" in mat:
        return 8.2 if weight_score >= 8 else 6.0
    elif "titanium" in mat:
        return 3.0
    elif "copper" in mat or "brass" in mat or "bronze" in mat:
        return 5.5
    return 6.0


def estimate_sustainability_score(material_name: str, strength_score: float) -> float:
    mat = str(material_name).lower()
    if "aluminum" in mat or "copper" in mat or "brass" in mat:
        return 7.5
    elif "steel" in mat and strength_score < 6:
        return 7.0
    return 5.0


def assign_recommendation(row) -> str:
    strength_score     = float(row.get("strength_score",     0.0))
    weight_score       = float(row.get("weight_score",       0.0))
    cost_score         = float(row.get("cost_score",         5.0))
    sustainability_score = float(row.get("sustainability_score", 5.0))

    if strength_score >= 8 and weight_score >= 7:
        return "High Performance Composite"
    elif strength_score >= 7 and cost_score >= 7:
        return "Structural Metal"
    elif weight_score >= 8 and cost_score >= 8:
        return "Lightweight Economy"
    elif sustainability_score >= 7:
        return "Eco-Friendly Material"
    else:
        return "General Purpose"


def score_materials(
    input_path="data_raw.csv",
    output_path="materials_scored.csv",
    decimals: int = 2,
) -> pd.DataFrame:
    input_file  = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found at: {input_file.resolve()}")

    print(f"Loading data from: {input_file.resolve()}")
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} material records.")

    df["Ultimate_Strength_MPa"] = pd.to_numeric(
        df["Ultimate_Strength_MPa"], errors="coerce")
    df["Density_kg_m3"] = pd.to_numeric(
        df["Density_kg_m3"], errors="coerce")
    df["Material_Cost_INR_per_kg"] = pd.to_numeric(
        df["Material_Cost_INR_per_kg"], errors="coerce")
    df["Embodied_Carbon_kgCO2e_per_kg"] = pd.to_numeric(
        df["Embodied_Carbon_kgCO2e_per_kg"], errors="coerce")

    df["strength_score"]      = compute_strength_score(
                                df["Ultimate_Strength_MPa"])
    df["weight_score"]        = compute_weight_score(
                                df["Density_kg_m3"])
    df["cost_score"]          = compute_cost_score(
                                df["Material_Cost_INR_per_kg"])
    df["sustainability_score"]= compute_sustainability_score(
                                df["Embodied_Carbon_kgCO2e_per_kg"])
    df["recommendation"] = df.apply(assign_recommendation, axis=1)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)
    print(f"Saved {len(df)} rows to: {output_file.resolve()}")
    return df


def load_materials(path="materials_scored.csv") -> pd.DataFrame:
    """
    Load already-scored materials CSV into a DataFrame.
    Call score_materials() first if the file does not exist.
    """
    scored = Path(path)
    if not scored.exists():
        print("materials_scored.csv not found. Running scorer first...")
        score_materials()
    return pd.read_csv(scored)


if __name__ == "__main__":
    base_dir   = Path(__file__).resolve().parent
    raw_csv    = base_dir / "data_raw.csv"
    scored_csv = base_dir / "materials_scored.csv"

    scored_df = score_materials(input_path=raw_csv, output_path=scored_csv)

    print("\n--- Recommendation Distribution ---")
    print(scored_df["recommendation"].value_counts())

    print("\n--- Preview ---")
    preview_cols = ["Material_Key","strength_score","weight_score",
                    "cost_score","sustainability_score","recommendation"]
    print(scored_df[preview_cols].head(10))
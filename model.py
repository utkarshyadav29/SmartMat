"""
SmartMat requirement-aware recommendation/ranking model.

This is the single live ranking engine used by api.py.
There is deliberately no Decision Tree here because the supplied dataset has
no independent ground-truth suitability labels.

Live flow:
    SmartMat_Master.csv
        -> hard constraints
        -> criterion scoring
        -> user-priority weighting
        -> ranked Top-N

materials_scored.csv is an optional export only and is never required by the
live API.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from scoring import add_criterion_scores, add_weighted_total, normalize_priorities


DEFAULT_PRIORITIES = {
    "strength": 5,
    "temperature": 5,
    "weight": 5,
    "cost": 5,
    "sustainability": 5,
}


def apply_hard_constraints(
    df: pd.DataFrame,
    required_yield_strength_mpa: Optional[float] = None,
    required_ultimate_strength_mpa: Optional[float] = None,
    required_temperature_c: Optional[float] = None,
    must_be_recyclable: bool = False,
    low_carbon_required: bool = False,
    eco_label_required: bool = False,
    bio_based_required: bool = False,
) -> pd.DataFrame:
    """Apply explicit engineering/sustainability requirements before scoring."""
    out = df.copy()

    if required_yield_strength_mpa is not None:
        out = out[
            pd.to_numeric(out["Yield_Strength_MPa"], errors="coerce")
            >= float(required_yield_strength_mpa)
        ]

    if required_ultimate_strength_mpa is not None:
        out = out[
            pd.to_numeric(out["Ultimate_Strength_MPa"], errors="coerce")
            >= float(required_ultimate_strength_mpa)
        ]

    if required_temperature_c is not None:
        out = out[
            pd.to_numeric(out["Max_Service_Temperature_C"], errors="coerce")
            >= float(required_temperature_c)
        ]

    if must_be_recyclable:
        out = out[out["Recyclable"].fillna(False).astype(bool)]

    if low_carbon_required:
        out = out[out["Low_Carbon"].fillna(False).astype(bool)]

    if eco_label_required:
        out = out[out["Eco_Label"].fillna(False).astype(bool)]

    if bio_based_required:
        out = out[out["Bio_Based"].fillna(False).astype(bool)]

    return out


def rank_materials(
    df: pd.DataFrame,
    priorities: dict[str, float],
    required_yield_strength_mpa: Optional[float] = None,
    required_ultimate_strength_mpa: Optional[float] = None,
    required_temperature_c: Optional[float] = None,
    must_be_recyclable: bool = False,
    low_carbon_required: bool = False,
    eco_label_required: bool = False,
    bio_based_required: bool = False,
    top_n: int = 5,
) -> pd.DataFrame:
    """Apply constraints and calculate a fresh ranking for this request."""
    required_keys = {
        "strength",
        "temperature",
        "weight",
        "cost",
        "sustainability",
    }
    missing = required_keys - set(priorities)
    if missing:
        raise KeyError(f"Missing priority keys: {sorted(missing)}")

    candidates = apply_hard_constraints(
        df,
        required_yield_strength_mpa=required_yield_strength_mpa,
        required_ultimate_strength_mpa=required_ultimate_strength_mpa,
        required_temperature_c=required_temperature_c,
        must_be_recyclable=must_be_recyclable,
        low_carbon_required=low_carbon_required,
        eco_label_required=eco_label_required,
        bio_based_required=bio_based_required,
    )

    if candidates.empty:
        return candidates.copy()

    scored = add_criterion_scores(
        candidates,
        required_yield_strength_mpa=required_yield_strength_mpa,
        required_ultimate_strength_mpa=required_ultimate_strength_mpa,
        required_temperature_c=required_temperature_c,
    )
    scored = add_weighted_total(scored, priorities)
    scored = scored.dropna(subset=["final_score"]).copy()

    scored = scored.sort_values(
        ["final_score", "strength_score", "weight_score", "cost_score"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    scored["rank"] = scored.index + 1

    weights = normalize_priorities(
        priorities["strength"],
        priorities["temperature"],
        priorities["weight"],
        priorities["cost"],
        priorities["sustainability"],
    )
    for criterion, weight in weights.items():
        scored[f"user_weight_{criterion}"] = weight

    return scored.head(int(top_n)).copy()


def explain_material(row: pd.Series) -> str:
    scores = {
        "strength": float(row["strength_score"]),
        "temperature": float(row["temperature_score"]),
        "weight": float(row["weight_score"]),
        "cost": float(row["cost_score"]),
        "sustainability": float(row["sustainability_score"]),
    }
    labels = {
        "strength": "strength",
        "temperature": "temperature resistance",
        "weight": "lightweight performance",
        "cost": "cost",
        "sustainability": "sustainability",
    }
    best = max(scores, key=scores.get)
    worst = min(scores, key=scores.get)
    return (
        f"Strongest criterion: {labels[best]} ({scores[best]:.1f}/10). "
        f"Weakest criterion: {labels[worst]} ({scores[worst]:.1f}/10). "
        f"Overall weighted score: {float(row['final_score']):.2f}/10."
    )


def recommend_from_csv(
    csv_path: str | Path = "SmartMat_Master.csv",
    priorities: Optional[dict[str, float]] = None,
    top_n: int = 5,
    **constraints,
) -> pd.DataFrame:
    """Load the master dataset and calculate a fresh Top-N ranking."""
    if priorities is None:
        priorities = DEFAULT_PRIORITIES.copy()

    df = pd.read_csv(csv_path)
    result = rank_materials(df, priorities=priorities, top_n=top_n, **constraints)
    if not result.empty:
        result["explanation"] = result.apply(explain_material, axis=1)
    return result


if __name__ == "__main__":
    df = pd.read_csv("SmartMat_Master.csv")
    examples = {
        "BALANCED": DEFAULT_PRIORITIES,
        "STRENGTH HEAVY": {
            "strength": 10,
            "temperature": 8,
            "weight": 6,
            "cost": 4,
            "sustainability": 5,
        },
        "LIGHTWEIGHT + COST": {
            "strength": 3,
            "temperature": 2,
            "weight": 10,
            "cost": 8,
            "sustainability": 5,
        },
    }

    for name, priorities in examples.items():
        print(f"\n=== {name} ===")
        result = rank_materials(df, priorities=priorities, top_n=5)
        print(
            result[
                [
                    "rank",
                    "Material_Key",
                    "Material_Family",
                    "strength_score",
                    "temperature_score",
                    "weight_score",
                    "cost_score",
                    "sustainability_score",
                    "final_score",
                    "total_score",
                ]
            ].to_string(index=False)
        )

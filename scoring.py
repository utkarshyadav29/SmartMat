"""
SmartMat requirement-aware scoring engine.

Single source of truth:
    SmartMat_Master.csv

This module calculates the five user-facing criteria scores and combines them
with the current dashboard priorities. It does NOT train a model.

The live API should call these functions on every recommendation request.
materials_scored.csv is only an optional generated/export file; it is NOT used
as the live recommendation source.

IMPORTANT DATA-QUALITY RULE
---------------------------
Materials with missing values in any of the six required engineering inputs
are retained in the knowledge base, but they are NOT eligible for ranking.

No missing engineering value is replaced with an artificial score.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


CRITERIA = [
    "strength",
    "temperature",
    "weight",
    "cost",
    "sustainability",
]


REQUIRED_MASTER_COLUMNS = [
    "Material_Key",
    "Yield_Strength_MPa",
    "Ultimate_Strength_MPa",
    "Density_kg_m3",
    "Material_Cost_INR_per_kg",
    "Embodied_Carbon_kgCO2e_per_kg",
    "Max_Service_Temperature_C",
]


RANKING_DATA_COLUMNS = [
    "Yield_Strength_MPa",
    "Ultimate_Strength_MPa",
    "Density_kg_m3",
    "Material_Cost_INR_per_kg",
    "Embodied_Carbon_kgCO2e_per_kg",
    "Max_Service_Temperature_C",
]


def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _safe_minmax_high(
    series: pd.Series,
    decimals: int = 2,
) -> pd.Series:
    """Higher value = better; scale to 1..10."""

    s = _safe_numeric(series)

    lo, hi = s.min(), s.max()

    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return pd.Series(
            5.0,
            index=s.index,
        )

    return (
        1.0
        + 9.0 * (s - lo) / (hi - lo)
    ).clip(
        1,
        10,
    ).round(decimals)


def _safe_minmax_low(
    series: pd.Series,
    decimals: int = 2,
) -> pd.Series:
    """Lower value = better; scale to 1..10."""

    s = _safe_numeric(series)

    lo, hi = s.min(), s.max()

    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return pd.Series(
            5.0,
            index=s.index,
        )

    return (
        1.0
        + 9.0 * (hi - s) / (hi - lo)
    ).clip(
        1,
        10,
    ).round(decimals)


def _requirement_score_high(
    series: pd.Series,
    requirement: Optional[float],
    decimals: int = 2,
) -> pd.Series:
    """Score performance against an optional minimum requirement."""

    if requirement is None:
        return _safe_minmax_high(
            series,
            decimals,
        )

    s = _safe_numeric(series)

    req = float(requirement)

    if req <= 0:
        return pd.Series(
            10.0,
            index=s.index,
        )

    return (
        10.0 * s / req
    ).clip(
        1,
        10,
    ).round(decimals)


def compute_strength_score(
    yield_strength: pd.Series,
    ultimate_strength: pd.Series,
    required_yield_strength_mpa: Optional[float] = None,
    required_ultimate_strength_mpa: Optional[float] = None,
    yield_weight: float = 0.70,
    decimals: int = 2,
) -> pd.Series:
    """Strength score = 70% yield strength + 30% UTS."""

    sy = _requirement_score_high(
        yield_strength,
        required_yield_strength_mpa,
        decimals,
    )

    su = _requirement_score_high(
        ultimate_strength,
        required_ultimate_strength_mpa,
        decimals,
    )

    return (
        yield_weight * sy
        + (1.0 - yield_weight) * su
    ).round(decimals)


def compute_weight_score(
    density_series: pd.Series,
    decimals: int = 2,
) -> pd.Series:
    return _safe_minmax_low(
        density_series,
        decimals,
    )


def compute_cost_score(
    cost_series: pd.Series,
    decimals: int = 2,
) -> pd.Series:
    return _safe_minmax_low(
        cost_series,
        decimals,
    )


def compute_sustainability_score(
    carbon_series: pd.Series,
    decimals: int = 2,
) -> pd.Series:
    return _safe_minmax_low(
        carbon_series,
        decimals,
    )


def compute_temperature_score(
    temperature_series: pd.Series,
    required_temperature_c: Optional[float] = None,
    decimals: int = 2,
) -> pd.Series:
    """Higher maximum service temperature = better."""

    return _requirement_score_high(
        temperature_series,
        required_temperature_c,
        decimals,
    )


def normalize_priorities(
    strength: float,
    temperature: float,
    weight: float,
    cost: float,
    sustainability: float,
) -> dict[str, float]:
    """Convert dashboard 1..10 priorities into weights summing to 1."""

    raw = {
        "strength": max(
            0.0,
            float(strength),
        ),

        "temperature": max(
            0.0,
            float(temperature),
        ),

        "weight": max(
            0.0,
            float(weight),
        ),

        "cost": max(
            0.0,
            float(cost),
        ),

        "sustainability": max(
            0.0,
            float(sustainability),
        ),
    }

    total = sum(
        raw.values()
    )

    if total <= 0:
        return {
            key: 1.0 / len(raw)
            for key in raw
        }

    return {
        key: value / total
        for key, value in raw.items()
    }


def validate_master_columns(
    df: pd.DataFrame,
) -> None:

    missing = [
        column
        for column in REQUIRED_MASTER_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise KeyError(
            "SmartMat_Master.csv is missing required columns: "
            + ", ".join(missing)
        )


def add_ranking_data_quality_flag(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Identify whether each material contains all required numerical
    engineering inputs needed for the five-criterion ranking.

    IMPORTANT:
    This does NOT delete incomplete materials.

    It only marks them as ineligible for ranking.
    """

    out = df.copy()

    numeric_data = (
        out[RANKING_DATA_COLUMNS]
        .apply(
            pd.to_numeric,
            errors="coerce",
        )
    )

    out["_ranking_data_complete"] = (
        numeric_data
        .notna()
        .all(axis=1)
    )

    return out


def add_criterion_scores(
    df: pd.DataFrame,
    required_yield_strength_mpa: Optional[float] = None,
    required_ultimate_strength_mpa: Optional[float] = None,
    required_temperature_c: Optional[float] = None,
    decimals: int = 2,
) -> pd.DataFrame:
    """
    Return a copy with the five live criterion scores.

    Materials with incomplete engineering data are retained but their
    criterion scores are set to NaN so they cannot receive a fake ranking.
    """

    validate_master_columns(df)

    out = df.copy()

    # -------------------------------------------------------------
    # DATA QUALITY FLAG
    # -------------------------------------------------------------

    out = add_ranking_data_quality_flag(
        out
    )

    # -------------------------------------------------------------
    # FIVE CRITERION SCORES
    # -------------------------------------------------------------

    out["strength_score"] = compute_strength_score(
        out["Yield_Strength_MPa"],
        out["Ultimate_Strength_MPa"],
        required_yield_strength_mpa,
        required_ultimate_strength_mpa,
        decimals=decimals,
    )

    out["temperature_score"] = compute_temperature_score(
        out["Max_Service_Temperature_C"],
        required_temperature_c,
        decimals,
    )

    out["weight_score"] = compute_weight_score(
        out["Density_kg_m3"],
        decimals,
    )

    out["cost_score"] = compute_cost_score(
        out["Material_Cost_INR_per_kg"],
        decimals,
    )

    out["sustainability_score"] = compute_sustainability_score(
        out["Embodied_Carbon_kgCO2e_per_kg"],
        decimals,
    )

    # -------------------------------------------------------------
    # IMPORTANT:
    # Prevent incomplete materials from receiving artificial scores.
    # -------------------------------------------------------------

    incomplete_mask = (
        ~out["_ranking_data_complete"]
    )

    score_columns = [
        "strength_score",
        "temperature_score",
        "weight_score",
        "cost_score",
        "sustainability_score",
    ]

    out.loc[
        incomplete_mask,
        score_columns,
    ] = np.nan

    return out


def add_weighted_total(
    df: pd.DataFrame,
    priorities: dict[str, float],
    decimals: int = 2,
) -> pd.DataFrame:
    """Add criterion contributions and the current final weighted score."""

    out = df.copy()

    weights = normalize_priorities(
        priorities["strength"],
        priorities["temperature"],
        priorities["weight"],
        priorities["cost"],
        priorities["sustainability"],
    )

    for criterion in CRITERIA:

        out[
            f"{criterion}_contribution"
        ] = (
            out[f"{criterion}_score"]
            * weights[criterion]
        )

        out[
            f"user_weight_{criterion}"
        ] = weights[criterion]

    out["final_score"] = sum(
        out[
            f"{criterion}_contribution"
        ]
        for criterion in CRITERIA
    ).round(decimals)

    out["total_score"] = (
        out["final_score"] * 10.0
    ).round(1)

    # -------------------------------------------------------------
    # IMPORTANT:
    # An incomplete material cannot have a valid final score.
    # -------------------------------------------------------------

    if "_ranking_data_complete" in out.columns:

        incomplete_mask = (
            ~out["_ranking_data_complete"]
        )

        out.loc[
            incomplete_mask,
            [
                "final_score",
                "total_score",
            ],
        ] = np.nan

    return out


def score_materials(
    input_path: str | Path = "SmartMat_Master.csv",
    output_path: str | Path = "materials_scored.csv",
    priorities: Optional[dict[str, float]] = None,
    required_yield_strength_mpa: Optional[float] = None,
    required_ultimate_strength_mpa: Optional[float] = None,
    required_temperature_c: Optional[float] = None,
) -> pd.DataFrame:
    """
    Generate an optional scored CSV from the current master dataset.

    Incomplete materials remain in the generated CSV but receive no rank.
    """

    if priorities is None:

        priorities = {
            criterion: 5
            for criterion in CRITERIA
        }

    input_path = Path(
        input_path
    )

    output_path = Path(
        output_path
    )

    if not input_path.exists():

        raise FileNotFoundError(
            f"Input file not found: "
            f"{input_path.resolve()}"
        )

    df = pd.read_csv(
        input_path
    )

    df = add_criterion_scores(
        df,
        required_yield_strength_mpa,
        required_ultimate_strength_mpa,
        required_temperature_c,
    )

    df = add_weighted_total(
        df,
        priorities,
    )

    # -------------------------------------------------------------
    # ONLY complete materials receive a rank.
    # -------------------------------------------------------------

    complete_mask = (
        df["_ranking_data_complete"]
    )

    df["rank"] = pd.Series(
        pd.NA,
        index=df.index,
        dtype="Int64",
    )

    complete_df = df.loc[
        complete_mask
    ].copy()

    if not complete_df.empty:

        complete_df["rank"] = (
            complete_df["final_score"]
            .rank(
                method="min",
                ascending=False,
            )
            .astype("Int64")
        )

        df.loc[
            complete_df.index,
            "rank",
        ] = complete_df["rank"]

    # -------------------------------------------------------------
    # Sort:
    # 1. Complete/rankable materials first
    # 2. Higher score
    # 3. Strength
    # 4. Weight
    # -------------------------------------------------------------

    result = df.sort_values(
        [
            "_ranking_data_complete",
            "final_score",
            "strength_score",
            "weight_score",
        ],
        ascending=[
            False,
            False,
            False,
            False,
        ],
        na_position="last",
    ).reset_index(
        drop=True
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        output_path,
        index=False,
    )

    return result


if __name__ == "__main__":

    scored = score_materials()

    print(
        scored[
            [
                "Material_Key",
                "_ranking_data_complete",
                "strength_score",
                "temperature_score",
                "weight_score",
                "cost_score",
                "sustainability_score",
                "final_score",
                "total_score",
                "rank",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    incomplete_count = int(
        (
            ~scored[
                "_ranking_data_complete"
            ]
        ).sum()
    )

    print(
        f"\nMaterials with incomplete "
        f"ranking data: {incomplete_count}"
    )
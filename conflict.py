"""
conflict.py
Detects engineering requirement trade-off conflicts when user criteria are mutually exclusive
or difficult to satisfy simultaneously, and suggests trade-off resolutions.
"""

from typing import Tuple, Dict, Any, Optional
import pandas as pd


def detect_conflict(ranked_df: pd.DataFrame, threshold: float = 55.0) -> Tuple[bool, Optional[str]]:
    """
    Checks if top ranked material scores below the specified threshold.
    If yes, finds which property has lowest average across top 5 materials
    and returns an actionable suggestion to relax constraints.

    Args:
        ranked_df: DataFrame sorted descending by total score.
        threshold: Score threshold (default 55.0 on a 100-point scale).

    Returns:
        tuple (conflict_detected: bool, message: str or None)
    """
    if ranked_df.empty:
        return True, "No materials matched the criteria. Please relax hard constraints."

    # Identify total score column
    score_col = None
    for cand in ["total_score", "total", "score"]:
        if cand in ranked_df.columns:
            score_col = cand
            break

    if score_col is None:
        return False, None

    top_row = ranked_df.iloc[0]
    top_score = float(top_row[score_col])

    # Standardize to 100-point scale if normalized on 10-point scale
    normalized_top_score = top_score * 10.0 if top_score <= 10.0 else top_score

    if normalized_top_score >= threshold:
        return False, None

    # Inspect top 5 materials to find lowest average property score
    top_5 = ranked_df.head(5)
    property_cols = {
        "Strength": ["strength_score", "strength"],
        "Weight / Lightweighting": ["weight_score", "weight"],
        "Cost Economy": ["cost_score", "cost"],
        "Elevated Temperature": ["temp_score", "temp"],
        "Sustainability": ["sustainability_score", "sustainability"],
    }

    avg_scores: Dict[str, float] = {}
    for prop_name, candidates in property_cols.items():
        for col in candidates:
            if col in top_5.columns:
                series_num = pd.to_numeric(top_5[col], errors="coerce")
                if series_num.notna().any():
                    # If on 1-10 scale, record mean
                    val = float(series_num.mean())
                    avg_scores[prop_name] = val
                    break

    if not avg_scores:
        msg = (
            f"Requirement conflict detected: Top match achieved {normalized_top_score:.1f}/100 "
            f"(target threshold: {threshold}). Consider relaxing priority sliders."
        )
        return True, msg

    lowest_prop = min(avg_scores, key=avg_scores.get)
    lowest_val = avg_scores[lowest_prop]

    message = (
        f"Requirement conflict detected: Top material scored {normalized_top_score:.1f}/100 "
        f"(below minimum threshold of {threshold:.1f}). "
        f"The primary bottleneck across top candidates is '{lowest_prop}' with an average score of "
        f"{lowest_val:.1f}/10. Suggest reducing '{lowest_prop}' priority by 20% to discover viable alternatives."
    )
    return True, message


def resolve_conflict(user_weights: Dict[str, float]) -> Dict[str, float]:
    """
    Takes user weight dict, finds the highest weight property,
    reduces it by 20%, and redistributes the difference among the remaining properties.

    Args:
        user_weights: Dict mapping property names to weights (e.g. 1-10).

    Returns:
        Suggested updated weights dict.
    """
    if not user_weights:
        return {}

    updated = {k: float(v) for k, v in user_weights.items()}
    highest_prop = max(updated, key=updated.get)
    highest_val = updated[highest_prop]

    reduction = highest_val * 0.20
    updated[highest_prop] = round(highest_val - reduction, 2)

    other_props = [k for k in updated if k != highest_prop]
    if other_props:
        redistribution_each = reduction / len(other_props)
        for k in other_props:
            updated[k] = round(updated[k] + redistribution_each, 2)

    return updated


if __name__ == "__main__":
    sample_df = pd.DataFrame({
        "Material_Key": [f"Mat_{i}" for i in range(5)],
        "total_score": [52.0, 50.0, 48.0, 45.0, 40.0],
        "strength_score": [8.0, 8.5, 7.9, 8.2, 8.0],
        "weight_score": [2.1, 2.3, 2.0, 1.9, 2.2],
        "cost_score": [6.0, 5.8, 6.2, 5.5, 5.9],
        "sustainability_score": [5.0, 5.2, 4.8, 5.0, 5.1],
    })

    conflict, msg = detect_conflict(sample_df, threshold=55.0)
    print("Conflict detected:", conflict)
    print("Message:", msg)

    test_weights = {"strength": 9, "weight": 9, "cost": 7, "temp": 5, "sustainability": 5}
    resolved = resolve_conflict(test_weights)
    print("Resolved weights:", resolved)

"""
field_rules.py
Hard minimum requirements that filter out unsuitable materials for automotive components
before running scoring algorithms.
"""

from typing import Dict, Any, Tuple, Optional, Union
import pandas as pd

# Hard minimum criteria per automotive component
FIELD_RULES: Dict[str, Dict[str, float]] = {
    "Engine Block": {
        "UTS_at_T_MPa": 200.0,
        "Thermal_Conductivity_W_mK": 30.0,
    },
    "Brake System": {
        "UTS_at_T_MPa": 200.0,
        "Thermal_Conductivity_W_mK": 20.0,
    },
    "Exhaust System": {
        "UTS_at_T_MPa": 150.0,
        "Thermal_Conductivity_W_mK": 15.0,
    },
    "Chassis": {
        "Ultimate_Strength_MPa": 400.0,
    },
    "Chassis / Frame": {
        "Ultimate_Strength_MPa": 400.0,
    },
    "Suspension": {
        "Ultimate_Strength_MPa": 500.0,
        "Elongation_percent": 10.0,
    },
    "Suspension Component": {
        "Ultimate_Strength_MPa": 500.0,
        "Elongation_percent": 10.0,
    },
    "Body Panel": {},
    "Body Panel / Skin": {},
    "Wheel/Rim": {
        "Ultimate_Strength_MPa": 300.0,
    },
    "Wheel / Rim": {
        "Ultimate_Strength_MPa": 300.0,
    },
    "Interior": {},
    "Interior Structure": {},
}


def _get_rules_for_component(component: str) -> Dict[str, float]:
    """Resolve component string (case-insensitive and partial match) to rule dict."""
    if not component:
        return {}
    if component in FIELD_RULES:
        return FIELD_RULES[component]

    comp_lower = component.lower()
    for key, rules in FIELD_RULES.items():
        if key.lower() == comp_lower or key.lower() in comp_lower or comp_lower in key.lower():
            return rules
    return {}


def apply_field_rules(
    df: pd.DataFrame,
    component: str,
    return_note: bool = False,
) -> Union[pd.DataFrame, Tuple[pd.DataFrame, Optional[str]]]:
    """
    Applies hard minimum thresholds for the specified automotive component.

    If the strict filter yields 0 materials, rules are relaxed by 20% and retried once.
    If still empty, returns the original DataFrame with a note.

    Args:
        df: Input DataFrame containing material properties.
        component: Automotive component name.
        return_note: If True, returns (filtered_df, note). Defaults to False (returns filtered_df with .attrs['note']).

    Returns:
        Filtered DataFrame, or tuple (filtered_df, note) if return_note is True.
    """
    if df.empty:
        note = "Input dataframe is empty."
        if return_note:
            return df, note
        df.attrs["rules_note"] = note
        return df

    rules = _get_rules_for_component(component)
    if not rules:
        note = f"No hard minimum field rules required for '{component}'."
        df_res = df.copy()
        df_res.attrs["rules_note"] = note
        return (df_res, note) if return_note else df_res

    # Apply strict rules
    mask = pd.Series(True, index=df.index)
    for col, min_val in rules.items():
        if col in df.columns:
            series_num = pd.to_numeric(df[col], errors="coerce")
            mask &= series_num >= min_val
        else:
            # Column not present; skip this specific constraint
            pass

    filtered_df = df[mask].copy()

    if not filtered_df.empty:
        note = f"Applied strict field rules for '{component}': {rules}. Matched {len(filtered_df)} candidates."
        filtered_df.attrs["rules_note"] = note
        return (filtered_df, note) if return_note else filtered_df

    # Relaxation step: relax thresholds by 20% (threshold * 0.8)
    relaxed_rules = {col: val * 0.8 for col, val in rules.items()}
    relaxed_mask = pd.Series(True, index=df.index)
    for col, min_val in relaxed_rules.items():
        if col in df.columns:
            series_num = pd.to_numeric(df[col], errors="coerce")
            relaxed_mask &= series_num >= min_val

    relaxed_df = df[relaxed_mask].copy()

    if not relaxed_df.empty:
        note = (
            f"Strict rules yielded 0 materials. Relaxed rules by 20% ({relaxed_rules}) "
            f"yielding {len(relaxed_df)} candidates."
        )
        relaxed_df.attrs["rules_note"] = note
        return (relaxed_df, note) if return_note else relaxed_df

    # Fallback if even relaxed rules return nothing
    note = (
        f"Strict and relaxed rules for '{component}' matched 0 materials. "
        "Returning unconstrained dataset."
    )
    fallback_df = df.copy()
    fallback_df.attrs["rules_note"] = note
    return (fallback_df, note) if return_note else fallback_df


def apply_field_rules_with_note(df: pd.DataFrame, component: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """Convenience helper that explicitly returns (filtered_df, note)."""
    return apply_field_rules(df, component, return_note=True)


if __name__ == "__main__":
    test_df = pd.DataFrame({
        "Material_Key": ["Mat A", "Mat B", "Mat C"],
        "Ultimate_Strength_MPa": [450, 320, 250],
        "UTS_at_T_MPa": [210, 180, 120],
        "Thermal_Conductivity_W_mK": [35, 25, 10],
        "Elongation_percent": [12, 15, 5],
    })

    chassis_filtered, note_chassis = apply_field_rules_with_note(test_df, "Chassis")
    print(f"Chassis Filtered: {len(chassis_filtered)} rows | Note: {note_chassis}")

    engine_filtered, note_engine = apply_field_rules_with_note(test_df, "Engine Block")
    print(f"Engine Filtered: {len(engine_filtered)} rows | Note: {note_engine}")
